import hashlib
import random
import uuid


DOMAINS = ["public-cloud", "private-cloud", "internal", "partner"]


def normalize_project_id(value: str) -> str:
    return str(uuid.UUID(value.strip()))


def build_account_details(project_id: str) -> dict[str, str]:
    normalized_project_id = normalize_project_id(project_id)
    return fetch_external_account(normalized_project_id)


def fetch_external_account(project_id: str) -> dict[str, str]:
    randomizer = random.Random(seed_for(project_id))

    return {
        "project_name": f"project-{project_id[:8]}",
        "domain": randomizer.choice(DOMAINS),
        "project_id": project_id,
    }


def seed_for(project_id: str) -> int:
    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)
