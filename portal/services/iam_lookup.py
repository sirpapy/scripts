from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
import hashlib
import json
import random
import re

from portal.services.object_storage import IamPolicyStatement, IamPolicyVersion


IGG_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{2,15}$")


@dataclass
class IamUser:
    username: str
    user_id: str
    arn: str
    creation_date: datetime | None


@dataclass
class IamAccessKey:
    username: str
    access_key_id: str
    creation_date: datetime | None
    status: str


@dataclass
class IamGroup:
    group_name: str
    arn: str
    group_id: str
    creation_date: datetime | None
    policies: list[IamPolicyVersion] = field(default_factory=list)


@dataclass(frozen=True)
class ConflictSource:
    group_name: str
    policy_name: str
    sid: str | None


@dataclass
class PermissionConflict:
    action: str
    deny: ConflictSource
    allowed_by: list[ConflictSource]


def get_iam_policy_by_user(access_key: str, igg: str, project_id: str, ring: str) -> dict:
    randomizer = random.Random(seed_for(igg, project_id, ring))

    requested_user = build_user_if_exists(randomizer, igg)
    requested_key = build_access_key_if_correct(randomizer, igg, access_key)
    iam_groups = build_groups_for_user(randomizer, igg, project_id) if requested_user else []
    conflicts = find_permission_conflicts(iam_groups)

    return {
        "is_user": requested_user is not None,
        "user": requested_user,
        "access_key_correct": requested_key is not None,
        "access_key": requested_key,
        "conflicts": conflicts,
        "iam_details": iam_groups,
    }


def find_permission_conflicts(iam_groups: list[IamGroup]) -> list[PermissionConflict]:
    deny_statements: list[tuple[str, str, IamPolicyStatement]] = []
    allow_statements: list[tuple[str, str, IamPolicyStatement]] = []

    for group in iam_groups:
        for policy in group.policies:
            for statement in policy.statements:
                entry = (group.group_name, policy.policy_name or "", statement)

                if statement.effect == "Deny":
                    deny_statements.append(entry)
                else:
                    allow_statements.append(entry)

    conflicts: list[PermissionConflict] = []

    for deny_group, deny_policy, deny_statement in deny_statements:
        for deny_action in deny_statement.actions:
            allowed_by = dedupe_sources([
                ConflictSource(allow_group, allow_policy, allow_statement.sid)
                for allow_group, allow_policy, allow_statement in allow_statements
                for allow_action in allow_statement.actions
                if actions_overlap(deny_action, allow_action)
            ])

            if allowed_by:
                conflicts.append(
                    PermissionConflict(
                        action=deny_action,
                        deny=ConflictSource(deny_group, deny_policy, deny_statement.sid),
                        allowed_by=allowed_by,
                    )
                )

    return conflicts


def actions_overlap(deny_action: str, allow_action: str) -> bool:
    return fnmatch(allow_action, deny_action) or fnmatch(deny_action, allow_action)


def dedupe_sources(sources: list[ConflictSource]) -> list[ConflictSource]:
    seen: set[ConflictSource] = set()
    deduped: list[ConflictSource] = []

    for source in sources:
        if source in seen:
            continue

        seen.add(source)
        deduped.append(source)

    return deduped


def build_user_if_exists(randomizer: random.Random, igg: str) -> IamUser | None:
    if not igg or not randomizer.choice([True, True, True, False]):
        return None

    return IamUser(
        username=igg,
        user_id=stable_uuid(igg, "user").replace("-", "").upper()[:21],
        arn=f"arn:aws:iam::{account_hash(igg)}:user/{igg}",
        creation_date=datetime.now(timezone.utc) - timedelta(days=randomizer.randrange(30, 1200)),
    )


def build_access_key_if_correct(
    randomizer: random.Random,
    igg: str,
    access_key: str,
) -> IamAccessKey | None:
    if not igg or not access_key:
        return None

    expected_access_key = f"AKIA{stable_uuid(igg, 'access-key').replace('-', '').upper()[:16]}"

    if access_key.strip() != expected_access_key:
        return None

    return IamAccessKey(
        username=igg,
        access_key_id=access_key.strip(),
        creation_date=datetime.now(timezone.utc) - timedelta(days=randomizer.randrange(5, 900)),
        status=randomizer.choice(["Active", "Active", "Active", "Inactive"]),
    )


def build_groups_for_user(randomizer: random.Random, igg: str, project_id: str) -> list[IamGroup]:
    group_names = randomizer.sample(
        ["s3-readers", "s3-writers", "s3-admins", "bucket-lifecycle-managers", "replication-operators"],
        k=randomizer.randrange(1, 4),
    )

    return [
        build_group(randomizer, igg, project_id, group_name)
        for group_name in group_names
    ]


def build_group(
    randomizer: random.Random,
    igg: str,
    project_id: str,
    group_name: str,
) -> IamGroup:
    created_at = datetime.now(timezone.utc) - timedelta(days=randomizer.randrange(60, 1500))

    return IamGroup(
        group_name=group_name,
        arn=f"arn:aws:iam::{account_hash(project_id)}:group/{group_name}",
        group_id=stable_uuid(project_id, group_name).replace("-", "").upper()[:21],
        creation_date=created_at,
        policies=build_policies_for_group(randomizer, project_id, group_name, created_at),
    )


def build_policies_for_group(
    randomizer: random.Random,
    project_id: str,
    group_name: str,
    created_at: datetime,
) -> list[IamPolicyVersion]:
    bucket_name = f"{account_slug(project_id)}-data"

    if group_name == "s3-readers":
        return [read_only_policy(project_id, bucket_name, created_at)]

    if group_name == "s3-writers":
        return [read_only_policy(project_id, bucket_name, created_at), write_policy(project_id, bucket_name, created_at)]

    if group_name == "s3-admins":
        return [full_access_policy(project_id, bucket_name, created_at)]

    if group_name == "bucket-lifecycle-managers":
        return [lifecycle_deny_delete_policy(project_id, bucket_name, created_at)]

    return [replication_policy(project_id, bucket_name, created_at)]


def read_only_policy(project_id: str, bucket_name: str, created_at: datetime) -> IamPolicyVersion:
    return IamPolicyVersion(
        version_id="v1",
        is_default_version=True,
        create_date=created_at,
        document_version="2012-10-17",
        policy_arn=policy_arn(project_id, "s3-read-only"),
        policy_name="s3-read-only",
        statements=[
            IamPolicyStatement(
                sid="AllowRead",
                effect="Allow",
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[bucket_arn(bucket_name), bucket_arn(bucket_name, "*")],
            )
        ],
    )


def write_policy(project_id: str, bucket_name: str, created_at: datetime) -> IamPolicyVersion:
    return IamPolicyVersion(
        version_id="v1",
        is_default_version=True,
        create_date=created_at + timedelta(hours=1),
        document_version="2012-10-17",
        policy_arn=policy_arn(project_id, "s3-write"),
        policy_name="s3-write",
        statements=[
            IamPolicyStatement(
                sid="AllowPutObject",
                effect="Allow",
                actions=["s3:PutObject", "s3:PutObjectAcl"],
                resources=[bucket_arn(bucket_name, "*")],
            ),
            IamPolicyStatement(
                sid="DenyDeleteObject",
                effect="Deny",
                actions=["s3:DeleteObject"],
                resources=[bucket_arn(bucket_name, "*")],
            ),
        ],
    )


def full_access_policy(project_id: str, bucket_name: str, created_at: datetime) -> IamPolicyVersion:
    return IamPolicyVersion(
        version_id="v1",
        is_default_version=True,
        create_date=created_at + timedelta(hours=2),
        document_version="2012-10-17",
        policy_arn=policy_arn(project_id, "s3-full-access"),
        policy_name="s3-full-access",
        statements=[
            IamPolicyStatement(
                sid="AllowAllS3",
                effect="Allow",
                actions=["s3:*"],
                resources=[bucket_arn(bucket_name), bucket_arn(bucket_name, "*")],
            )
        ],
    )


def lifecycle_deny_delete_policy(project_id: str, bucket_name: str, created_at: datetime) -> IamPolicyVersion:
    return IamPolicyVersion(
        version_id="v1",
        is_default_version=True,
        create_date=created_at + timedelta(hours=3),
        document_version="2012-10-17",
        policy_arn=policy_arn(project_id, "bucket-lifecycle"),
        policy_name="bucket-lifecycle",
        statements=[
            IamPolicyStatement(
                sid="AllowLifecycle",
                effect="Allow",
                actions=["s3:PutLifecycleConfiguration", "s3:GetLifecycleConfiguration"],
                resources=[bucket_arn(bucket_name)],
            ),
            IamPolicyStatement(
                sid="DenyDeleteBucket",
                effect="Deny",
                actions=["s3:DeleteBucket"],
                resources=[bucket_arn(bucket_name)],
            ),
        ],
    )


def replication_policy(project_id: str, bucket_name: str, created_at: datetime) -> IamPolicyVersion:
    return IamPolicyVersion(
        version_id="v1",
        is_default_version=True,
        create_date=created_at + timedelta(hours=4),
        document_version="2012-10-17",
        policy_arn=policy_arn(project_id, "s3-replication"),
        policy_name="s3-replication",
        statements=[
            IamPolicyStatement(
                sid="AllowReplicationRead",
                effect="Allow",
                actions=["s3:GetReplicationConfiguration", "s3:ListBucket"],
                resources=[bucket_arn(bucket_name)],
            ),
            IamPolicyStatement(
                sid="AllowReplicateObjects",
                effect="Allow",
                actions=["s3:ReplicateObject", "s3:ReplicateDelete"],
                resources=[bucket_arn(bucket_name, "*")],
            ),
        ],
    )


def normalize_igg(value: str) -> str:
    igg = value.strip()

    if not IGG_PATTERN.match(igg):
        raise ValueError("Invalid IGG")

    return igg


def bucket_arn(bucket_name: str, suffix: str | None = None) -> str:
    arn = f"arn:aws:s3:::{bucket_name}"

    return f"{arn}/{suffix}" if suffix else arn


def policy_arn(project_id: str, policy_name: str) -> str:
    return f"arn:aws:iam::{account_hash(project_id)}:policy/{policy_name}"


def account_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def account_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    return slug[:42] or "account"


def stable_uuid(*parts: str) -> str:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-"
        f"{digest[16:20]}-{digest[20:32]}"
    )


def seed_for(*parts: str) -> int:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def iam_group_as_dict(group: IamGroup) -> dict[str, object]:
    return {
        "GroupName": group.group_name,
        "Arn": group.arn,
        "GroupId": group.group_id,
        "CreateDate": iso_date(group.creation_date),
        "Policies": [policy.as_dict() for policy in group.policies],
    }


def iam_details_json(iam_groups: list[IamGroup]) -> str:
    return json.dumps([iam_group_as_dict(group) for group in iam_groups], indent=2)


def iso_date(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.isoformat()
