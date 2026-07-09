from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import random
import re


BUCKET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
REPLICATION_BIDIRECTIONAL = "bidirectional"
REPLICATION_INBOUND = "inbound"
REPLICATION_NONE = "none"
REPLICATION_OUTBOUND = "outbound"


def default_principals() -> list[str]:
    return ["*"]


@dataclass(frozen=True)
class ReplicationDetails:
    direction: str
    source_bucket: str
    target_bucket: str | None = None
    peer_bucket: str | None = None

    @property
    def enabled(self) -> bool:
        return self.direction != REPLICATION_NONE and self.target_bucket is not None


@dataclass(frozen=True)
class IamPolicyStatement:
    effect: str
    actions: list[str]
    resources: list[str]
    principals: list[str] = field(default_factory=default_principals)
    sid: str | None = None

    @property
    def s3_bucket_names(self) -> list[str]:
        names: list[str] = []

        for resource in self.resources:
            bucket_name = bucket_name_from_arn(resource)

            if bucket_name and bucket_name not in names:
                names.append(bucket_name)

        return names

    def as_dict(self) -> dict[str, object]:
        statement = {
            "Effect": self.effect,
            "Action": self.actions,
            "Resource": self.resources,
            "Principal": {"AWS": self.principals},
        }

        if self.sid:
            statement["Sid"] = self.sid

        return statement


@dataclass(frozen=True)
class IamPolicyVersion:
    version_id: str
    is_default_version: bool
    create_date: datetime | None
    document_version: str
    policy_arn: str
    policy_name: str
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


@dataclass(frozen=True)
class BucketDetails:
    ring: str
    name: str
    owner: str
    owner_display_name: str
    creation_date: datetime | None
    location_constraint: str
    deleted: bool = False
    transient: bool = False
    object_lock_enabled: bool = False
    model_version: int = 7
    bucket_policy_present: bool = False
    cors_present: bool = False
    lifecycle_present: bool = False
    server_side_encryption_present: bool = False
    versioning_enabled: bool = False
    notification_present: bool = False
    object_lock_mode: str | None = None
    object_lock_retention_days: int | None = None
    replication_direction: str = REPLICATION_NONE
    replication_destination: str | None = None
    replication_peer: str | None = None
    replication_source: str | None = None
    replication_target: str | None = None
    tags: list[dict[str, str]] = field(default_factory=list)
    iam_policy_versions: list[IamPolicyVersion] = field(default_factory=list)
    uid: str | None = None

    @property
    def policies_json(self) -> str:
        return json.dumps(
            [
                policy.as_dict()
                for policy in self.iam_policy_versions
            ],
            indent=2,
        )

    @property
    def bucket_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    def as_dict(self) -> dict[str, object]:
        return {
            "ring": self.ring,
            "name": self.name,
            "owner": self.owner,
            "ownerDisplayName": self.owner_display_name,
            "creationDate": iso_date(self.creation_date),
            "locationConstraint": self.location_constraint,
            "deleted": self.deleted,
            "transient": self.transient,
            "objectLockEnabled": self.object_lock_enabled,
            "mdBucketModelVersion": self.model_version,
            "bucketPolicy": self.bucket_policy_present,
            "cors": self.cors_present,
            "lifecycleConfiguration": self.lifecycle_present,
            "objectLockConfiguration": {
                "mode": self.object_lock_mode,
                "retentionDays": self.object_lock_retention_days,
            } if self.object_lock_enabled else None,
            "replicationDirection": self.replication_direction,
            "replicationDestination": self.replication_destination,
            "replicationPeer": self.replication_peer,
            "replicationSource": self.replication_source,
            "replicationTarget": self.replication_target,
            "serverSideEncryption": self.server_side_encryption_present,
            "versioningConfiguration": self.versioning_enabled,
            "notificationConfiguration": self.notification_present,
            "tags": self.tags,
            "uid": self.uid,
        }

    @property
    def touched_buckets(self) -> list[str]:
        names: list[str] = []

        for policy in self.iam_policy_versions:
            for bucket_name in policy.touched_buckets:
                if bucket_name not in names:
                    names.append(bucket_name)

        return names

    @property
    def replication_enabled(self) -> bool:
        return self.replication_direction != REPLICATION_NONE


def get_bucket_policy_report(bucket_name: str, ring: str) -> BucketDetails:
    bucket_name = normalize_bucket_name(bucket_name)
    randomizer = random.Random(seed_for(bucket_name, ring))
    created_at = datetime.now(timezone.utc) - timedelta(
        days=randomizer.randrange(20, 900)
    )
    owner_id = stable_uuid(bucket_name, ring, "owner")
    replication = replication_details_for(bucket_name)
    object_lock_enabled = randomizer.choice([True, False])

    return BucketDetails(
        ring=ring,
        name=bucket_name,
        owner=bucket_owner(owner_id),
        owner_display_name=owner_id,
        creation_date=created_at,
        location_constraint=randomizer.choice(["dc-1", "dc-2", "eu-1"]),
        deleted=False,
        transient=False,
        object_lock_enabled=object_lock_enabled,
        bucket_policy_present=False,
        cors_present=randomizer.choice([False, False, True]),
        lifecycle_present=randomizer.choice([False, False, True]),
        server_side_encryption_present=randomizer.choice([False, True]),
        versioning_enabled=replication.enabled,
        notification_present=randomizer.choice([False, False, True]),
        object_lock_mode="Governance" if object_lock_enabled else None,
        object_lock_retention_days=1 if object_lock_enabled else None,
        replication_direction=replication.direction,
        replication_destination=replication.target_bucket,
        replication_peer=replication.peer_bucket,
        replication_source=replication.source_bucket,
        replication_target=replication.target_bucket,
        tags=[
            {"key": "owner", "value": bucket_owner(owner_id)},
            {"key": "ring", "value": ring},
        ],
        iam_policy_versions=build_policy_versions(bucket_name, replication, created_at),
        uid=stable_uuid(bucket_name, ring, "bucket"),
    )


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
