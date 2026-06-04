from dataclasses import dataclass
import hashlib
import random
import uuid


QUOTA_FIELDS = [
    {
        "key": "volumes",
        "label": "Number of volumes",
        "unit": "volumes",
        "openstack_name": "volumes",
    },
    {
        "key": "gigabytes",
        "label": "Size total",
        "unit": "GiB",
        "openstack_name": "gigabytes",
    },
]


@dataclass(frozen=True)
class ProjectQuota:
    project_id: str
    openstack_version: str
    region: str
    volumes_limit: int
    gigabytes_limit: int


@dataclass(frozen=True)
class QuotaRequest:
    project_id: str
    openstack_version: str
    region: str
    requested_volumes: int | None
    requested_gigabytes: int | None


def normalize_project_id(value: str) -> str:
    return str(uuid.UUID(value.strip()))


def parse_positive_int(value: str) -> int | None:
    cleaned = str(value or "").strip()

    if not cleaned:
        return None

    parsed = int(cleaned)

    if parsed < 0:
        raise ValueError("value must be positive")

    return parsed


def build_request(
    project_id: str,
    openstack_version: str,
    region: str,
    requested_volumes: str,
    requested_gigabytes: str,
) -> QuotaRequest:
    return QuotaRequest(
        project_id=normalize_project_id(project_id),
        openstack_version=openstack_version,
        region=region,
        requested_volumes=parse_positive_int(requested_volumes),
        requested_gigabytes=parse_positive_int(requested_gigabytes),
    )


def build_quota(
    project_id: str,
    openstack_version: str,
    region: str,
    overrides: dict[str, dict[str, int]] | None = None,
) -> ProjectQuota:
    randomizer = random.Random(seed_for(project_id, openstack_version, region))
    volumes_limit = randomizer.randrange(20, 151, 10)
    gigabytes_limit = randomizer.randrange(500, 5001, 100)

    override = (overrides or {}).get(
        quota_key(project_id, openstack_version, region)
    )

    if override:
        volumes_limit = override.get("volumes", volumes_limit)
        gigabytes_limit = override.get("gigabytes", gigabytes_limit)

    return ProjectQuota(
        project_id=project_id,
        openstack_version=openstack_version,
        region=region,
        volumes_limit=volumes_limit,
        gigabytes_limit=gigabytes_limit,
    )


def quota_rows(quota: ProjectQuota, request: QuotaRequest | None = None) -> list[dict[str, object]]:
    requested = {
        "volumes": request.requested_volumes if request else None,
        "gigabytes": request.requested_gigabytes if request else None,
    }
    current = {
        "volumes": quota.volumes_limit,
        "gigabytes": quota.gigabytes_limit,
    }
    rows = []

    for field in QUOTA_FIELDS:
        key = field["key"]
        requested_value = requested[key]
        current_limit = current[key]
        delta = None if requested_value is None else requested_value - current_limit

        rows.append(
            {
                "key": key,
                "label": field["label"],
                "unit": field["unit"],
                "openstack_name": field["openstack_name"],
                "current_limit": current_limit,
                "requested": requested_value,
                "delta": delta,
                "is_increase": delta is not None and delta > 0,
                "is_unchanged": delta is None or delta == 0,
            }
        )

    return rows


def request_has_change(quota: ProjectQuota, request: QuotaRequest) -> bool:
    for row in quota_rows(quota, request):
        if row["delta"] not in (None, 0):
            return True

    return False


def request_is_increase_only(quota: ProjectQuota, request: QuotaRequest) -> bool:
    rows = quota_rows(quota, request)
    return all(row["delta"] is None or row["delta"] >= 0 for row in rows)


def apply_request(
    overrides: dict[str, dict[str, int]],
    quota: ProjectQuota,
    request: QuotaRequest,
) -> dict[str, dict[str, int]]:
    key = quota_key(
        request.project_id,
        request.openstack_version,
        request.region,
    )
    existing = overrides.get(key, {})
    volumes = quota.volumes_limit
    gigabytes = quota.gigabytes_limit

    if request.requested_volumes is not None:
        volumes = request.requested_volumes

    if request.requested_gigabytes is not None:
        gigabytes = request.requested_gigabytes

    next_values = {
        "volumes": volumes,
        "gigabytes": gigabytes,
    }

    existing.update(next_values)
    overrides[key] = existing
    return overrides


def quota_key(project_id: str, openstack_version: str, region: str) -> str:
    return f"{project_id}@{openstack_version}@{region}"


def seed_for(project_id: str, openstack_version: str, region: str) -> int:
    digest = hashlib.sha256(
        f"{project_id}:{openstack_version}:{region}".encode("utf-8")
    ).hexdigest()
    return int(digest[:16], 16)
