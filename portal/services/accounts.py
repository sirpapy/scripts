from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import random
import re
import uuid

from portal.services import object_storage


ACCOUNT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{3,80}$")
DOMAINS = ["public-cloud", "private-cloud", "internal", "partner"]


def normalize_project_id(value: str) -> str:
    return str(uuid.UUID(value.strip()))


def build_account_details(project_id: str) -> dict[str, str]:
    normalized_project_id = normalize_project_id(project_id)
    return fetch_external_account(normalized_project_id)


@dataclass(frozen=True)
class AccountReport:
    account_id: str
    project_name: str
    domain: str
    project_id: str
    owner_display_name: str
    iam_policy_versions: list[object_storage.IamPolicyVersion] = field(
        default_factory=list
    )

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
    def account_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    @property
    def touched_buckets(self) -> list[str]:
        names: list[str] = []

        for policy in self.iam_policy_versions:
            for bucket_name in policy.touched_buckets:
                if bucket_name not in names:
                    names.append(bucket_name)

        return names

    def as_dict(self) -> dict[str, object]:
        return {
            "account_id": self.account_id,
            "project_name": self.project_name,
            "domain": self.domain,
            "project_id": self.project_id,
            "owner_display_name": self.owner_display_name,
            "iam_policy_versions": [
                policy.as_dict()
                for policy in self.iam_policy_versions
            ],
        }


def normalize_account_id(value: str) -> str:
    account_id = value.strip()

    if not ACCOUNT_ID_PATTERN.match(account_id):
        raise ValueError("Invalid account ID")

    return account_id


def build_account_report(account_id: str) -> AccountReport:
    account_id = normalize_account_id(account_id)
    account = fetch_account_by_id(account_id)

    return AccountReport(
        account_id=account_id,
        project_name=account["project_name"],
        domain=account["domain"],
        project_id=account["project_id"],
        owner_display_name=account["owner_display_name"],
        iam_policy_versions=build_account_policies(account_id),
    )


def fetch_external_account(project_id: str) -> dict[str, str]:
    randomizer = random.Random(seed_for(project_id))

    return {
        "project_name": f"project-{project_id[:8]}",
        "domain": randomizer.choice(DOMAINS),
        "project_id": project_id,
    }


def fetch_account_by_id(account_id: str) -> dict[str, str]:
    randomizer = random.Random(seed_for(account_id))

    return {
        "project_name": f"project-{account_slug(account_id)}",
        "domain": randomizer.choice(DOMAINS),
        "project_id": stable_uuid(account_id, "project"),
        "owner_display_name": stable_uuid(account_id, "owner"),
    }


def build_account_policies(account_id: str) -> list[object_storage.IamPolicyVersion]:
    slug = account_slug(account_id)
    created_at = datetime.now(timezone.utc) - timedelta(days=90)
    source_bucket = bucket_name(slug, "source")
    target_bucket = bucket_name(slug, "target")
    logs_bucket = bucket_name(slug, "logs")

    return [
        object_storage.IamPolicyVersion(
            version_id="v1",
            is_default_version=True,
            create_date=created_at,
            document_version="2012-10-17",
            policy_arn=account_policy_arn(account_id, "read"),
            policy_name=f"{slug}-read",
            statements=[
                object_storage.IamPolicyStatement(
                    sid="ReadAccountBuckets",
                    effect="Allow",
                    actions=[
                        "s3:ListBucket",
                        "s3:GetObject",
                        "s3:GetObjectVersion",
                    ],
                    resources=[
                        object_storage.bucket_arn(source_bucket),
                        object_storage.bucket_arn(source_bucket, "*"),
                        object_storage.bucket_arn(logs_bucket, "*"),
                    ],
                )
            ],
        ),
        object_storage.IamPolicyVersion(
            version_id="v1",
            is_default_version=True,
            create_date=created_at + timedelta(hours=2),
            document_version="2012-10-17",
            policy_arn=account_policy_arn(account_id, "replication"),
            policy_name=f"{slug}-replication",
            statements=[
                object_storage.IamPolicyStatement(
                    sid="ReadReplicationConfig",
                    effect="Allow",
                    actions=["s3:GetReplicationConfiguration"],
                    resources=[object_storage.bucket_arn(source_bucket)],
                ),
                object_storage.IamPolicyStatement(
                    sid="ReplicateObjects",
                    effect="Allow",
                    actions=[
                        "s3:ReplicateObject",
                        "s3:ReplicateDelete",
                    ],
                    resources=[
                        object_storage.bucket_arn(source_bucket, "*"),
                        object_storage.bucket_arn(target_bucket, "*"),
                    ],
                ),
            ],
        ),
    ]


def account_slug(account_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", account_id.lower()).strip("-")

    return slug[:42] or "account"


def bucket_name(slug: str, suffix: str) -> str:
    return f"{slug[:50]}-{suffix}"


def account_policy_arn(account_id: str, policy_type: str) -> str:
    account_hash = hashlib.sha1(account_id.encode("utf-8")).hexdigest()[:12]
    policy_name = f"{account_slug(account_id)}-{policy_type}"

    return f"arn:aws:iam::{account_hash}:policy/{policy_name}"


def stable_uuid(*parts: str) -> str:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-"
        f"{digest[16:20]}-{digest[20:32]}"
    )


def seed_for(project_id: str) -> int:
    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)
