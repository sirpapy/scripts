from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import random
import re
from typing import Any


BUCKET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
REPLICATION_BIDIRECTIONAL = "bidirectional"
REPLICATION_INBOUND = "inbound"
REPLICATION_NONE = "none"
REPLICATION_OUTBOUND = "outbound"


@dataclass
class RingEndpoint:
    url: str
    name: str
    region: str
    offer: str
    ring: str
    endpoint: str


@dataclass
class BucketAcl:
    canned: str
    full_control: list[str] = field(default_factory=list)
    read: list[str] = field(default_factory=list)
    read_acp: list[str] = field(default_factory=list)
    write: list[str] = field(default_factory=list)
    write_acp: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "canned": self.canned,
            "full_control": self.full_control,
            "read": self.read,
            "read_acp": self.read_acp,
            "write": self.write,
            "write_acp": self.write_acp,
        }


@dataclass(frozen=True)
class ReplicationDetails:
    direction: str
    source_bucket: str
    target_bucket: str | None = None
    peer_bucket: str | None = None

    @property
    def enabled(self) -> bool:
        return self.direction != REPLICATION_NONE and self.target_bucket is not None


@dataclass
class IamPolicyStatement:
    effect: str
    actions: list[str]
    resources: list[str]
    sid: str | None = None

    @property
    def s3_bucket_names(self) -> list[str]:
        bucket_names: list[str] = []

        for resource in self.resources:
            if not resource.startswith("arn:aws:s3:::"):
                continue

            bucket_name = resource.replace(
                "arn:aws:s3:::",
                "",
                1,
            ).split("/", 1)[0]

            if bucket_name and bucket_name not in bucket_names:
                bucket_names.append(bucket_name)

        return bucket_names

    def as_dict(self) -> dict[str, object]:
        statement = {
            "Effect": self.effect,
            "Action": self.actions,
            "Resource": self.resources,
            "Principal": {"AWS": ["*"]},
        }

        if self.sid:
            statement["Sid"] = self.sid

        return statement


@dataclass
class IamPolicyVersion:
    version_id: str
    is_default_version: bool
    create_date: datetime | None
    document_version: str | None = None
    policy_arn: str | None = None
    policy_name: str | None = None
    statements: list[IamPolicyStatement] = field(default_factory=list)

    @property
    def allowed_actions(self) -> list[str]:
        actions: list[str] = []

        for statement in self.statements:
            if statement.effect != "Allow":
                continue

            for action in statement.actions:
                if action not in actions:
                    actions.append(action)

        return actions

    @property
    def touched_buckets(self) -> list[str]:
        bucket_names: list[str] = []

        for statement in self.statements:
            for bucket_name in statement.s3_bucket_names:
                if bucket_name not in bucket_names:
                    bucket_names.append(bucket_name)

        return bucket_names

    @property
    def json_document(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    def as_dict(self) -> dict[str, object]:
        return {
            "PolicyName": self.policy_name,
            "PolicyArn": self.policy_arn,
            "DefaultVersionId": self.version_id,
            "PolicyVersion": {
                "VersionId": self.version_id,
                "IsDefaultVersion": self.is_default_version,
                "CreateDate": iso_date(self.create_date),
                "Document": {
                    "Version": self.document_version,
                    "Statement": [
                        statement.as_dict()
                        for statement in self.statements
                    ],
                },
            },
        }


@dataclass
class BucketDetails:
    ring: str
    name: str
    owner: str
    owner_display_name: str
    creation_date: datetime | None
    location_constraint: str
    acl: BucketAcl
    deleted: bool = False
    transient: bool = False
    object_lock_enabled: bool = False
    md_bucket_model_version: int = 7
    bucket_policy: Any | None = None
    cors: Any | None = None
    lifecycle_configuration: Any | None = None
    object_lock_configuration: Any | None = None
    replication_configuration: Any | None = None
    replication_destination: str | None = None
    iam_policy_versions: list[IamPolicyVersion] = field(default_factory=list)
    server_side_encryption: Any | None = None
    versioning_configuration: Any | None = None
    notification_configuration: Any | None = None
    tags: list[dict[str, str]] = field(default_factory=list)
    uid: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "ring": self.ring,
            "name": self.name,
            "owner": self.owner,
            "ownerDisplayName": self.owner_display_name,
            "creationDate": iso_date(self.creation_date),
            "locationConstraint": self.location_constraint,
            "acl": self.acl.as_dict(),
            "deleted": self.deleted,
            "transient": self.transient,
            "objectLockEnabled": self.object_lock_enabled,
            "mdBucketModelVersion": self.md_bucket_model_version,
            "bucketPolicy": self.bucket_policy,
            "cors": self.cors,
            "lifecycleConfiguration": self.lifecycle_configuration,
            "objectLockConfiguration": self.object_lock_configuration,
            "replicationConfiguration": self.replication_configuration,
            "replicationDestination": self.replication_destination,
            "serverSideEncryption": self.server_side_encryption,
            "versioningConfiguration": self.versioning_configuration,
            "notificationConfiguration": self.notification_configuration,
            "tags": self.tags,
            "uid": self.uid,
        }

    @property
    def replication_destination_bucket(self) -> str | None:
        if not self.replication_destination:
            return None

        return self.replication_destination.rsplit(":::", 1)[-1]

    @property
    def touched_buckets(self) -> list[str]:
        names: list[str] = []

        for policy in self.iam_policy_versions:
            for bucket_name in policy.touched_buckets:
                if bucket_name not in names:
                    names.append(bucket_name)

        return names


def get_bucket_policy_report(bucket_name: str, ring: str) -> BucketDetails:
    candidates = get_bucket_details(bucket_name, ring)
    return build_bucket_details(candidates[0])


def get_bucket_policy_reports(bucket_name: str, ring: str) -> list[BucketDetails]:
    return [
        build_bucket_details(candidate)
        for candidate in get_bucket_details(bucket_name, ring)
    ]


def get_bucket_details(bucket_name: str, ring: str) -> list[dict[str, Any]]:
    bucket_name = normalize_bucket_name(bucket_name)

    return [
        build_bucket_candidate(candidate, ring)
        for candidate in bucket_matches_for(bucket_name)
    ]


def bucket_matches_for(bucket_name: str) -> list[str]:
    matches = [bucket_name]
    replication = replication_details_for(bucket_name)

    if replication.peer_bucket and replication.peer_bucket not in matches:
        matches.append(replication.peer_bucket)

    return matches


def build_bucket_candidate(bucket_name: str, ring: str) -> dict[str, Any]:
    randomizer = random.Random(seed_for(bucket_name, ring))
    created_at = datetime.now(timezone.utc) - timedelta(
        days=randomizer.randrange(20, 900)
    )
    owner_id = stable_uuid(bucket_name, ring, "owner")
    replication = replication_details_for(bucket_name)
    object_lock_enabled = randomizer.choice([True, False])

    return {
        "ring": ring,
        "name": bucket_name,
        "owner": bucket_owner(owner_id),
        "owner_display_name": owner_id,
        "creation_date": created_at,
        "location_constraint": randomizer.choice(["dc-1", "dc-2", "eu-1"]),
        "acl": BucketAcl(canned="private"),
        "deleted": False,
        "transient": False,
        "object_lock_enabled": object_lock_enabled,
        "md_bucket_model_version": 7,
        "bucket_policy": None,
        "cors": example_config(randomizer, {"rules": []}),
        "lifecycle_configuration": example_config(randomizer, {"rules": []}),
        "object_lock_configuration": object_lock_config(object_lock_enabled),
        "replication_configuration": replication_config(replication),
        "replication_destination": replication_destination(replication),
        "iam_policy_versions": build_policy_versions(bucket_name, replication, created_at),
        "server_side_encryption": example_config(randomizer, {"algorithm": "AES256"}),
        "versioning_configuration": {"status": "Enabled"} if replication.enabled else None,
        "notification_configuration": example_config(randomizer, {"events": []}),
        "tags": [
            {"key": "owner", "value": bucket_owner(owner_id)},
            {"key": "ring", "value": ring},
        ],
        "uid": stable_uuid(bucket_name, ring, "bucket"),
    }


def build_bucket_details(candidate: dict[str, Any]) -> BucketDetails:
    return BucketDetails(
        ring=candidate["ring"],
        name=candidate["name"],
        owner=candidate["owner"],
        owner_display_name=candidate["owner_display_name"],
        creation_date=candidate["creation_date"],
        location_constraint=candidate["location_constraint"],
        acl=build_bucket_acl(candidate["acl"]),
        deleted=candidate.get("deleted", False),
        transient=candidate.get("transient", False),
        object_lock_enabled=candidate.get("object_lock_enabled", False),
        md_bucket_model_version=candidate.get("md_bucket_model_version", 7),
        bucket_policy=candidate.get("bucket_policy"),
        cors=candidate.get("cors"),
        lifecycle_configuration=candidate.get("lifecycle_configuration"),
        object_lock_configuration=candidate.get("object_lock_configuration"),
        replication_configuration=candidate.get("replication_configuration"),
        replication_destination=candidate.get("replication_destination"),
        iam_policy_versions=candidate.get("iam_policy_versions", []),
        server_side_encryption=candidate.get("server_side_encryption"),
        versioning_configuration=candidate.get("versioning_configuration"),
        notification_configuration=candidate.get("notification_configuration"),
        tags=candidate.get("tags", []),
        uid=candidate.get("uid"),
    )


def build_bucket_acl(value: BucketAcl | dict[str, Any]) -> BucketAcl:
    if isinstance(value, BucketAcl):
        return value

    return BucketAcl(
        canned=value.get("canned", ""),
        full_control=value.get("full_control", []),
        read=value.get("read", []),
        read_acp=value.get("read_acp", []),
        write=value.get("write", []),
        write_acp=value.get("write_acp", []),
    )


def bucket_candidate_json(candidate: dict[str, Any]) -> str:
    return json.dumps(json_value(candidate), indent=2)


def policy_versions_json(policies: list[IamPolicyVersion]) -> str:
    return json.dumps(
        [
            policy.as_dict()
            for policy in policies
        ],
        indent=2,
    )


def json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return iso_date(value)

    if isinstance(value, BucketAcl):
        return value.as_dict()

    if isinstance(value, IamPolicyVersion):
        return value.as_dict()

    if isinstance(value, IamPolicyStatement):
        return value.as_dict()

    if isinstance(value, dict):
        return {
            key: json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            json_value(item)
            for item in value
        ]

    return value


def example_config(randomizer: random.Random, value: dict[str, object]) -> dict[str, object] | None:
    if randomizer.choice([False, False, True]):
        return value

    return None


def object_lock_config(enabled: bool) -> dict[str, object] | None:
    if not enabled:
        return None

    return {
        "mode": "Governance",
        "retentionDays": 1,
    }


def replication_config(replication: ReplicationDetails) -> dict[str, str] | None:
    if not replication.enabled:
        return None

    config = {
        "direction": replication.direction,
        "source_bucket": replication.source_bucket,
        "target_bucket": replication.target_bucket or "",
    }

    if replication.peer_bucket:
        config["peer_bucket"] = replication.peer_bucket

    return config


def replication_destination(replication: ReplicationDetails) -> str | None:
    if not replication.target_bucket:
        return None

    return bucket_arn(replication.target_bucket)


def normalize_bucket_name(value: str) -> str:
    bucket_name = value.strip()

    if not BUCKET_NAME_PATTERN.match(bucket_name):
        raise ValueError("Invalid bucket name")

    return bucket_name


def build_policy_versions(
    bucket_name: str,
    replication: ReplicationDetails,
    created_at: datetime,
) -> list[IamPolicyVersion]:
    policies: list[IamPolicyVersion | None] = [build_read_policy(bucket_name, created_at)]

    if replication.enabled:
        policies.append(
            build_replication_policy(
                replication.source_bucket,
                replication.target_bucket,
                created_at,
            )
        )

    if replication.direction == REPLICATION_BIDIRECTIONAL:
        policies.append(
            build_replication_policy(
                replication.target_bucket,
                replication.source_bucket,
                created_at,
            )
        )

    return [
        policy
        for policy in policies
        if policy is not None
    ]


def build_read_policy(bucket_name: str, created_at: datetime) -> IamPolicyVersion:
    return IamPolicyVersion(
        version_id="v1",
        is_default_version=True,
        create_date=created_at + timedelta(minutes=12),
        document_version="2012-10-17",
        policy_arn=policy_arn(bucket_name, "read"),
        policy_name=f"{bucket_name}-read",
        statements=[
            IamPolicyStatement(
                sid="ReadBucketVersions",
                effect="Allow",
                actions=[
                    "s3:ListBucket",
                    "s3:GetObjectVersion",
                    "s3:GetObjectVersionAcl",
                ],
                resources=[
                    bucket_arn(bucket_name),
                    bucket_arn(bucket_name, "*"),
                ],
            )
        ],
    )


def build_replication_policy(
    bucket_name: str,
    destination: str,
    created_at: datetime,
) -> IamPolicyVersion | None:
    return IamPolicyVersion(
        version_id="v1",
        is_default_version=True,
        create_date=created_at + timedelta(hours=2),
        document_version="2012-10-17",
        policy_arn=policy_arn(bucket_name, "replication"),
        policy_name=f"{bucket_name}-replication",
        statements=[
            IamPolicyStatement(
                sid="ReadReplicationConfig",
                effect="Allow",
                actions=["s3:GetReplicationConfiguration"],
                resources=[bucket_arn(bucket_name)],
            ),
            IamPolicyStatement(
                sid="ReplicateObjects",
                effect="Allow",
                actions=[
                    "s3:ReplicateObject",
                    "s3:ReplicateDelete",
                ],
                resources=[
                    bucket_arn(bucket_name, "*"),
                    bucket_arn(destination, "*"),
                ],
            ),
        ],
    )


def replication_details_for(bucket_name: str) -> ReplicationDetails:
    if "mirror-a" in bucket_name:
        peer_bucket = bucket_name.replace("mirror-a", "mirror-b", 1)
        return ReplicationDetails(
            direction=REPLICATION_BIDIRECTIONAL,
            source_bucket=bucket_name,
            target_bucket=peer_bucket,
            peer_bucket=peer_bucket,
        )

    if "mirror-b" in bucket_name:
        peer_bucket = bucket_name.replace("mirror-b", "mirror-a", 1)
        return ReplicationDetails(
            direction=REPLICATION_BIDIRECTIONAL,
            source_bucket=bucket_name,
            target_bucket=peer_bucket,
            peer_bucket=peer_bucket,
        )

    if "source" in bucket_name:
        target_bucket = bucket_name.replace("source", "target", 1)
        return ReplicationDetails(
            direction=REPLICATION_OUTBOUND,
            source_bucket=bucket_name,
            target_bucket=target_bucket,
            peer_bucket=target_bucket,
        )

    if "target" in bucket_name:
        source_bucket = bucket_name.replace("target", "source", 1)
        return ReplicationDetails(
            direction=REPLICATION_INBOUND,
            source_bucket=source_bucket,
            target_bucket=bucket_name,
            peer_bucket=source_bucket,
        )

    return ReplicationDetails(direction=REPLICATION_NONE, source_bucket=bucket_name)


def bucket_arn(bucket_name: str, suffix: str | None = None) -> str:
    arn = f"arn:aws:s3:::{bucket_name}"

    if suffix:
        return f"{arn}/{suffix}"

    return arn


def bucket_name_from_arn(resource: str) -> str | None:
    prefix = "arn:aws:s3:::"

    if not resource.startswith(prefix):
        return None

    bucket_part = resource[len(prefix):]
    bucket_name = bucket_part.split("/", 1)[0]

    return bucket_name or None


def policy_arn(bucket_name: str, policy_type: str) -> str:
    account_id = hashlib.sha1(bucket_name.encode("utf-8")).hexdigest()[:12]
    return f"arn:aws:iam::{account_id}:policy/{bucket_name}-{policy_type}"


def bucket_owner(owner_id: str) -> str:
    owner_hash = hashlib.sha1(owner_id.encode("utf-8")).hexdigest()[:8]
    return f"OBJ_{owner_hash.upper()}_PRD"


def stable_uuid(*parts: str) -> str:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-"
        f"{digest[16:20]}-{digest[20:32]}"
    )


def seed_for(bucket_name: str, ring: str) -> int:
    digest = hashlib.sha256(f"{bucket_name}:{ring}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def iso_date(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.isoformat()
