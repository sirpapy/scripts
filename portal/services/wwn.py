from dataclasses import dataclass
import hashlib
import random

from portal.services import cinder


@dataclass(frozen=True)
class WwnVolumeMatch:
    wwn: str
    volume: cinder.Volume
    backend: str
    pool: str
    host_path: str


BACKENDS = ["ceph-ssd", "ceph-hdd", "lvm", "nvme-array"]
POOLS = ["pool-a", "pool-b", "gold", "silver", "archive"]


def parse_wwns(raw_input: str) -> list[str]:
    tokens = raw_input.replace(",", " ").split()
    unique_wwns = []
    seen = set()

    for token in tokens:
        cleaned = token.strip().lower()

        if cleaned and cleaned not in seen:
            unique_wwns.append(cleaned)
            seen.add(cleaned)

    return unique_wwns


def build_matches(
    raw_input: str,
    openstack_version: str,
    regions: list[str],
) -> list[WwnVolumeMatch]:
    return [
        build_match(wwn, openstack_version, regions)
        for wwn in parse_wwns(raw_input)
    ]


def build_match(
    wwn: str,
    openstack_version: str,
    regions: list[str],
) -> WwnVolumeMatch:
    randomizer = random.Random(seed_for(wwn))
    region = randomizer.choice(regions)
    volume_id = f"vol-{hashlib.sha1(wwn.encode('utf-8')).hexdigest()[:12]}"
    volume = cinder.build_volume(volume_id, openstack_version, region)
    backend = randomizer.choice(BACKENDS)
    pool = randomizer.choice(POOLS)

    return WwnVolumeMatch(
        wwn=wwn,
        volume=volume,
        backend=backend,
        pool=pool,
        host_path=f"{backend}/{pool}/{volume_id}",
    )


def seed_for(wwn: str) -> int:
    digest = hashlib.sha256(wwn.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)
