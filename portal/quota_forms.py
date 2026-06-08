from portal.services import quotas
from portal.view_helpers import (
    openstack_regions,
    openstack_versions_config,
    selected_openstack_version,
    selected_region,
)


def quota_retrieve_form_data(data):
    openstack_versions = openstack_versions_config()
    regions = openstack_regions()

    return {
        "project_id": data.get("project_id", "").strip(),
        "openstack_version": selected_openstack_version(
            data.get("openstack_version"),
            openstack_versions,
        ),
        "region": selected_region(data.get("region"), regions),
    }


def quota_decision_form_data(data):
    form_data = quota_retrieve_form_data(data)
    form_data["volumes"] = data.get("volumes", "").strip()
    form_data["gigabytes"] = data.get("gigabytes", "").strip()
    return form_data


def parse_project_lookup_or_none(form_data):
    try:
        return {
            "project_id": quotas.normalize_project_id(form_data["project_id"]),
            "openstack_version": form_data["openstack_version"],
            "region": form_data["region"],
        }
    except (TypeError, ValueError):
        return None


def parse_quota_request_or_none(form_data):
    try:
        return quotas.build_request(
            project_id=form_data["project_id"],
            openstack_version=form_data["openstack_version"],
            region=form_data["region"],
            requested_volumes=form_data["volumes"],
            requested_gigabytes=form_data["gigabytes"],
        )
    except (TypeError, ValueError):
        return None
