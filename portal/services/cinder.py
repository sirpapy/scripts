from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import random


VOLUME_TYPES = ["__DEFAULT__", "lvmdriver-1", "ceph-ssd", "ceph-hdd", "nvme"]
STATUSES = [
    "available",
    "in-use",
    "error",
    "attaching",
    "detaching",
    "reserved",
    "maintenance",
    "error_deleting",
]
FILTER_ORDER = [
    "available",
    "in-use",
    "reserved",
    "attaching",
    "detaching",
    "maintenance",
    "error",
    "error_deleting",
]

DEVICES = ["/dev/vda", "/dev/vdb", "/dev/vdc", "/dev/vdd", "/dev/sdb"]
HOSTS = ["cinder@ceph#ceph", "cinder@lvm#LVM", "cinder@nvme#NVMe", "hostgroup@ceph#ceph-ssd"]
VOLUME_NAMES = ["data-volume", "boot-disk", "db-storage", "backup-vol", "app-data", "logs-vol"]
IMAGES = ["ubuntu-22.04", "debian-12", "centos-stream-9", "rocky-9", "fedora-40"]


@dataclass(frozen=True)
class Attachment:
    server_id: str
    attachment_id: str
    device: str
    host_name: str


@dataclass(frozen=True)
class Volume:
    id: str
    openstack_version: str
    region: str
    status: str
    type: str
    size: int
    created: datetime
    updated: datetime
    name: str | None
    description: str | None
    bootable: bool
    multiattach: bool
    encrypted: bool
    availability_zone: str
    host: str
    tenant_id: str
    user_id: str
    replication_status: str
    snapshot_id: str | None
    source_volid: str | None
    image_metadata: dict[str, str] | None
    properties: dict[str, str]
    attachment: Attachment | None

    @property
    def is_deletable(self) -> bool:
        return self.status == "available"

    @property
    def can_reset(self) -> bool:
        return self.status != "available"


def parse_ids(raw_input: str) -> list[str]:
    tokens = raw_input.replace(",", " ").split()
    unique_ids: list[str] = []
    seen = set()

    for token in tokens:
        cleaned = token.strip()

        if cleaned and cleaned not in seen:
            unique_ids.append(cleaned)
            seen.add(cleaned)

    return unique_ids


def build_volumes(
    ids: list[str],
    openstack_version: str,
    region: str,
    deleted_keys: set[str] | None = None,
    reset_keys: set[str] | None = None,
) -> list[Volume]:
    deleted_keys = deleted_keys or set()
    reset_keys = reset_keys or set()
    volumes: list[Volume] = []

    for volume_id in ids:
        key = volume_key(volume_id, openstack_version, region)

        if key in deleted_keys:
            continue

        volume = build_volume(volume_id, openstack_version, region)

        if key in reset_keys:
            volume = reset_volume(volume)

        volumes.append(volume)

    return volumes


def build_volume(volume_id: str, openstack_version: str, region: str) -> Volume:
    randomizer = random.Random(seed_for(volume_id, openstack_version, region))

    status = randomizer.choice(STATUSES)
    size = 10 + randomizer.randrange(491)
    created = datetime.now(timezone.utc) - timedelta(days=randomizer.randrange(540))
    age_in_days = max(1, (datetime.now(timezone.utc) - created).days)
    updated = created + timedelta(days=randomizer.randrange(age_in_days))

    bootable = randomizer.random() < 0.3
    attached = status in {"in-use", "detaching"}
    attachment = build_attachment(randomizer) if attached else None
    image_metadata = build_image_metadata(randomizer, size) if bootable else None

    return Volume(
        id=volume_id,
        openstack_version=openstack_version,
        region=region,
        status=status,
        type=randomizer.choice(VOLUME_TYPES),
        size=size,
        created=created,
        updated=updated,
        name=volume_name(randomizer),
        description="Volume provisionne automatiquement" if randomizer.random() >= 0.7 else None,
        bootable=bootable,
        multiattach=randomizer.random() < 0.1,
        encrypted=randomizer.random() < 0.2,
        availability_zone=region,
        host=randomizer.choice(HOSTS),
        tenant_id=random_uuid(randomizer),
        user_id=random_uuid(randomizer),
        replication_status="disabled",
        snapshot_id=random_uuid(randomizer) if randomizer.random() < 0.15 else None,
        source_volid=random_uuid(randomizer) if randomizer.random() < 0.1 else None,
        image_metadata=image_metadata,
        properties={"attached_mode": "rw", "readonly": "False"} if attachment else {},
        attachment=attachment,
    )


def reset_volume(volume: Volume) -> Volume:
    return Volume(
        id=volume.id,
        openstack_version=volume.openstack_version,
        region=volume.region,
        status="available",
        type=volume.type,
        size=volume.size,
        created=volume.created,
        updated=datetime.now(timezone.utc),
        name=volume.name,
        description=volume.description,
        bootable=volume.bootable,
        multiattach=volume.multiattach,
        encrypted=volume.encrypted,
        availability_zone=volume.availability_zone,
        host=volume.host,
        tenant_id=volume.tenant_id,
        user_id=volume.user_id,
        replication_status=volume.replication_status,
        snapshot_id=volume.snapshot_id,
        source_volid=volume.source_volid,
        image_metadata=volume.image_metadata,
        properties={},
        attachment=None,
    )


def status_counts(volumes: list[Volume]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for volume in volumes:
        counts[volume.status] = counts.get(volume.status, 0) + 1

    return counts


def available_statuses(volumes: list[Volume]) -> list[str]:
    counts = status_counts(volumes)
    return [status for status in FILTER_ORDER if counts.get(status, 0) > 0]


def filtered_volumes(volumes: list[Volume], selected_statuses: set[str]) -> list[Volume]:
    if not selected_statuses:
        return volumes

    return [volume for volume in volumes if volume.status in selected_statuses]


def volume_key(volume_id: str, openstack_version: str, region: str) -> str:
    return f"{volume_id}@{openstack_version}@{region}"


def seed_for(volume_id: str, openstack_version: str, region: str) -> int:
    digest = hashlib.sha256(
        f"{volume_id}:{openstack_version}:{region}".encode("utf-8")
    ).hexdigest()
    return int(digest[:16], 16)


def build_attachment(randomizer: random.Random) -> Attachment:
    host_number = str(1 + randomizer.randrange(12)).zfill(2)

    return Attachment(
        server_id=random_uuid(randomizer),
        attachment_id=random_uuid(randomizer),
        device=randomizer.choice(DEVICES),
        host_name=f"compute-{host_number}",
    )


def build_image_metadata(randomizer: random.Random, size: int) -> dict[str, str]:
    return {
        "image_name": randomizer.choice(IMAGES),
        "image_id": random_uuid(randomizer),
        "container_format": "bare",
        "disk_format": "qcow2",
        "min_disk": str(size),
        "min_ram": "0",
    }


def volume_name(randomizer: random.Random) -> str | None:
    if randomizer.random() < 0.35:
        return None

    return f"{randomizer.choice(VOLUME_NAMES)}-{random_hex(randomizer, 4)}"


def random_uuid(randomizer: random.Random) -> str:
    variant = randomizer.choice("89ab")
    groups = [
        random_hex(randomizer, 8),
        random_hex(randomizer, 4),
        "4" + random_hex(randomizer, 3),
        variant + random_hex(randomizer, 3),
        random_hex(randomizer, 12),
    ]

    return "-".join(groups)


def random_hex(randomizer: random.Random, length: int) -> str:
    characters = "0123456789abcdef"
    return "".join(randomizer.choice(characters) for _ in range(length))


def cinder_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000")
