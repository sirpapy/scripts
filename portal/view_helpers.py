from django.conf import settings


def openstack_regions():
    regions = list(settings.OPENSTACK_REGIONS)

    if not regions:
        return ["us-east-1"]

    return regions


def openstack_versions_config():
    versions = list(settings.OPENSTACK_VERSIONS)

    if not versions:
        return ["v1"]

    return versions


def selected_openstack_version(value, openstack_versions):
    if value in openstack_versions:
        return value

    return openstack_versions[0]


def selected_region(value, regions):
    if value in regions:
        return value

    return regions[0]


def session_set(request, key):
    return set(request.session.get(key, []))


def input_token_count(raw_input):
    return len(raw_input.replace(",", " ").split())
