from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
import hashlib
import json
import random
import re

from portal.services.object_storage import IamPolicyStatement, IamPolicyVersion


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


def get_iam_policy_by_user(access_key: str, igg: str, project_id: str, ring: str) -> dict:
    user_randomizer = random.Random(seed_for(igg, project_id, ring, "user"))
    key_randomizer = random.Random(seed_for(igg, project_id, ring, "key"))
    groups_randomizer = random.Random(seed_for(igg, project_id, ring, "groups"))

    requested_user = build_user_if_exists(user_randomizer, igg)
    requested_key = build_access_key_if_correct(key_randomizer, igg, access_key)
    iam_groups = build_groups_for_user(groups_randomizer, igg, project_id) if requested_user else []
    conflicts = find_permission_conflicts(iam_groups)

    return {
        "is_user": requested_user is not None,
        "user": requested_user,
        "access_key_correct": requested_key is not None,
        "access_key": requested_key,
        "conflicts": conflicts,
        "iam_details": iam_groups,
    }


def find_permission_conflicts(iam_groups: list[IamGroup]) -> list[dict]:
    """Regle IAM : un Deny explicite l'emporte sur un Allow, meme si les deux
    viennent de groupes differents. Retourne un conflit par action refusee
    qu'un statement Allow accorde par ailleurs."""
    allows = []
    denies = []

    for group in iam_groups:
        for policy in group.policies:
            for statement in policy.statements:
                source = {
                    "group_name": group.group_name,
                    "policy_name": policy.policy_name,
                    "sid": statement.sid,
                }
                for action in statement.actions:
                    if statement.effect == "Deny":
                        denies.append((action, source))
                    else:
                        allows.append((action, source))

    conflicts = []

    for deny_action, deny_source in denies:
        allowed_by = []

        for allow_action, allow_source in allows:
            # fnmatch dans les deux sens pour couvrir les wildcards IAM :
            # un Allow s3:* couvre un Deny s3:DeleteObject, et inversement.
            overlap = fnmatch(allow_action, deny_action) or fnmatch(deny_action, allow_action)

            if overlap and allow_source not in allowed_by:
                allowed_by.append(allow_source)

        if allowed_by:
            conflicts.append({
                "action": deny_action,
                "deny": deny_source,
                "allowed_by": allowed_by,
            })

    return conflicts


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


def iam_details_json(iam_groups: list[IamGroup]) -> str:
    return json.dumps(
        [
            {
                "GroupName": group.group_name,
                "Arn": group.arn,
                "GroupId": group.group_id,
                "CreateDate": group.creation_date.isoformat() if group.creation_date else None,
                "Policies": [policy.as_dict() for policy in group.policies],
            }
            for group in iam_groups
        ],
        indent=2,
    )
