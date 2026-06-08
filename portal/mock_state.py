from portal.services import cinder
from portal.view_helpers import session_set


def quota_overrides(request):
    return dict(request.session.get("quota_overrides", {}))


def mark_reset(request, openstack_version, region, volume_ids):
    reset_keys = session_set(request, "reset_volumes")
    deleted_keys = session_set(request, "deleted_volumes")

    for volume_id in volume_ids:
        key = cinder.volume_key(volume_id, openstack_version, region)
        reset_keys.add(key)
        deleted_keys.discard(key)

    request.session["reset_volumes"] = sorted(reset_keys)
    request.session["deleted_volumes"] = sorted(deleted_keys)


def mark_deleted(request, openstack_version, region, volume_ids):
    deleted_keys = session_set(request, "deleted_volumes")
    reset_keys = session_set(request, "reset_volumes")

    for volume_id in volume_ids:
        key = cinder.volume_key(volume_id, openstack_version, region)
        deleted_keys.add(key)
        reset_keys.discard(key)

    request.session["deleted_volumes"] = sorted(deleted_keys)
    request.session["reset_volumes"] = sorted(reset_keys)
