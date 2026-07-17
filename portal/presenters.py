from dataclasses import asdict
import json
from urllib.parse import urlencode

from django.urls import reverse

from portal.services import cinder, iam_lookup, wwn
from portal.view_helpers import input_token_count


def annotate_cancelled_allows(check_list):
    """Pose statement.cancelled_by sur chaque Allow annule par un Deny d'un
    autre groupe, pour que le template affiche la chip "annule par"."""
    for group in check_list["iam_details"]:
        for policy in group.policies:
            for statement in policy.statements:
                source = {
                    "group_name": group.group_name,
                    "policy_name": policy.policy_name,
                    "sid": statement.sid,
                }
                statement.cancelled_by = [
                    conflict
                    for conflict in check_list["conflicts"]
                    if source in conflict["allowed_by"]
                ]


def iam_json_exports(check_list):
    """JSON des boutons Copier de la page de debogage IAM."""
    user = check_list["user"]
    access_key = check_list["access_key"]

    return {
        "user_json": json.dumps(asdict(user), indent=2, default=str) if user else "",
        "access_key_json": json.dumps(asdict(access_key), indent=2, default=str) if access_key else "",
        "iam_details_json": iam_lookup.iam_details_json(check_list["iam_details"]),
    }


def build_filter_links(volumes):
    counts = cinder.status_counts(volumes)
    links = [
        {
            "label": "Tous",
            "status": "",
            "count": len(volumes),
            "active": True,
            "css_class": "all",
        }
    ]

    for status in cinder.available_statuses(volumes):
        links.append(
            {
                "label": status,
                "status": status,
                "count": counts[status],
                "active": False,
                "css_class": status,
            }
        )

    return links


def volume_fields(volume):
    fields = [
        {"key": "attachments", "value": attachment_items(volume), "is_attachments": True},
        {"key": "openstack_version", "value": volume.openstack_version, "mono": True},
        {"key": "availability_zone", "value": volume.availability_zone, "mono": True},
        {"key": "bootable", "value": str(volume.bootable), "mono": True},
        {"key": "consistencygroup_id", "value": None},
        {"key": "created_at", "value": cinder.cinder_time(volume.created), "mono": True},
        {"key": "description", "value": volume.description},
        {"key": "encrypted", "value": str(volume.encrypted), "mono": True},
        {"key": "id", "value": volume.id, "mono": True},
        {"key": "multiattach", "value": str(volume.multiattach), "mono": True},
        {"key": "name", "value": volume.name, "mono": True},
        {"key": "os-vol-host-attr:host", "value": volume.host, "mono": True},
        {
            "key": "os-vol-tenant-attr:tenant_id",
            "value": volume.tenant_id,
            "mono": True,
            "is_account_link": True,
        },
        {"key": "properties", "value": volume.properties, "is_mapping": True},
        {"key": "replication_status", "value": volume.replication_status, "mono": True},
        {"key": "size", "value": f"{volume.size} GiB", "mono": True},
        {"key": "snapshot_id", "value": volume.snapshot_id, "mono": True},
        {"key": "source_volid", "value": volume.source_volid, "mono": True},
        {"key": "status", "value": volume.status, "is_status": True},
        {"key": "type", "value": volume.type, "mono": True},
        {"key": "updated_at", "value": cinder.cinder_time(volume.updated), "mono": True},
        {"key": "user_id", "value": volume.user_id, "mono": True},
    ]

    if volume.image_metadata:
        fields.append(
            {
                "key": "volume_image_metadata",
                "value": volume.image_metadata,
                "is_mapping": True,
            }
        )

    return fields


def attachment_items(volume):
    if not volume.attachment:
        return []

    attachment = volume.attachment

    return [
        {"key": "server_id", "value": attachment.server_id},
        {"key": "attachment_id", "value": attachment.attachment_id},
        {"key": "device", "value": attachment.device},
        {"key": "host_name", "value": attachment.host_name},
    ]


def volume_parse_hint(raw_ids):
    volume_ids = cinder.parse_ids(raw_ids)
    duplicate_count = input_token_count(raw_ids) - len(volume_ids)

    if not volume_ids:
        return "Aucun ID saisi."

    label = "ID unique" if len(volume_ids) == 1 else "IDs uniques"

    if duplicate_count == 0:
        return f"{len(volume_ids)} {label}"

    duplicate_label = "doublon ignore" if duplicate_count == 1 else "doublons ignores"
    return f"{len(volume_ids)} {label} - {duplicate_count} {duplicate_label}"


def wwn_parse_hint(raw_wwns):
    wwns = wwn.parse_wwns(raw_wwns)
    duplicate_count = input_token_count(raw_wwns) - len(wwns)

    if not wwns:
        return "Aucun WWN saisi."

    label = "WWN unique" if len(wwns) == 1 else "WWN uniques"

    if duplicate_count == 0:
        return f"{len(wwns)} {label}"

    duplicate_label = "doublon ignore" if duplicate_count == 1 else "doublons ignores"
    return f"{len(wwns)} {label} - {duplicate_count} {duplicate_label}"


def volumes_url(openstack_version, region, raw_ids, statuses=None):
    query = [
        ("openstack_version", openstack_version),
        ("region", region),
        ("ids", raw_ids),
    ]

    for status in sorted(statuses or []):
        query.append(("status", status))

    return f"{reverse('volumes')}?{urlencode(query)}"
