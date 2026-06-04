from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from portal.services import accounts, cinder, quotas, wwn


BLOCK_STORAGE_TOOLS = [
    {
        "id": "volumes",
        "route_name": "volumes",
        "title": "Gestionnaire de Volumes",
        "category": "Stockage",
        "icon_name": "HardDrive",
        "description": (
            "Recherchez, analysez, réinitialisez et supprimez vos volumes "
            "de stockage cloud."
        ),
    },
    {
        "id": "quotas",
        "route_name": "quotas",
        "title": "Gestionnaire de Quotas",
        "category": "Capacité",
        "icon_name": "Server",
        "description": (
            "Contrôlez les quotas Cinder d'un projet et préparez les "
            "augmentations demandées."
        ),
    },
    {
        "id": "accounts",
        "route_name": "accounts",
        "title": "Recherche Account",
        "category": "Identité",
        "icon_name": "Search",
        "description": "Récupérez les détails d'un account à partir d'un Project ID.",
    },
    {
        "id": "wwn",
        "route_name": "wwn_lookup",
        "title": "Recherche WWN",
        "category": "Stockage",
        "icon_name": "Link",
        "description": "Retrouvez les volumes correspondant à un ou plusieurs WWN.",
    }
]


TOOL_GROUPS = [
    {
        "id": "block-storage-tools",
        "title": "Block Storage Tools",
        "description": "Outils Cinder pour les volumes, quotas et recherches de stockage bloc.",
        "tools": BLOCK_STORAGE_TOOLS,
    },
    {
        "id": "object-storage-tools",
        "title": "Object Storage Tools",
        "description": "Outils Swift et stockage objet.",
        "tools": [],
    },
    {
        "id": "common-tools",
        "title": "Common Tools",
        "description": "Outils transverses partagés entre plusieurs plateformes.",
        "tools": [],
    },
]


@login_required
def index(request):
    return render(request, "portal/dashboard.html", {"tool_groups": TOOL_GROUPS})


@login_required
def volumes(request):
    if request.method == "POST":
        return handle_volume_action(request)

    openstack_versions = openstack_versions_config()
    openstack_version = selected_openstack_version(
        request.GET.get("openstack_version"),
        openstack_versions,
    )
    regions = openstack_regions()
    region = selected_region(request.GET.get("region"), regions)
    raw_ids = request.GET.get("ids", "")
    selected_statuses = set(request.GET.getlist("status"))
    ids = cinder.parse_ids(raw_ids)
    searched = "ids" in request.GET

    all_volumes = cinder.build_volumes(
        ids=ids,
        openstack_version=openstack_version,
        region=region,
        deleted_keys=session_set(request, "deleted_volumes"),
        reset_keys=session_set(request, "reset_volumes"),
    )
    displayed_volumes = cinder.filtered_volumes(all_volumes, selected_statuses)
    displayed_rows = [
        {"volume": volume, "fields": volume_fields(volume)}
        for volume in displayed_volumes
    ]

    context = {
        "regions": regions,
        "openstack_versions": openstack_versions,
        "openstack_version": openstack_version,
        "region": region,
        "raw_ids": raw_ids,
        "parse_hint": volume_parse_hint(raw_ids),
        "searched": searched,
        "volumes": all_volumes,
        "displayed_volumes": displayed_volumes,
        "displayed_rows": displayed_rows,
        "status_counts": cinder.status_counts(all_volumes),
        "present_statuses": cinder.available_statuses(all_volumes),
        "selected_statuses": selected_statuses,
        "filter_links": build_filter_links(
            request,
            openstack_version,
            region,
            raw_ids,
            all_volumes,
            selected_statuses,
        ),
    }

    return render(request, "portal/volumes.html", context)


@login_required
def quota_manager(request):
    if request.method == "POST":
        return handle_quota_action(request)

    context = build_quota_context(request)
    return render(request, "portal/quotas.html", context)


@login_required
def account_lookup(request):
    project_id = request.GET.get("project_id", "").strip()
    account_details = None
    searched = "project_id" in request.GET

    if project_id:
        try:
            account_details = accounts.build_account_details(project_id)
        except ValueError:
            messages.error(request, "Project ID invalide. Le Project ID doit etre un UUID.")
    elif searched:
        messages.error(request, "Saisissez un Project ID.")

    return render(
        request,
        "portal/accounts.html",
        {
            "project_id": project_id,
            "account": account_details,
            "searched": searched,
        },
    )


@login_required
def wwn_lookup(request):
    raw_wwns = request.GET.get("wwns", "")
    searched = "wwns" in request.GET
    matches = wwn.build_matches(
        raw_wwns,
        openstack_versions_config()[0],
        openstack_regions(),
    ) if searched else []

    return render(
        request,
        "portal/wwn_lookup.html",
        {
            "raw_wwns": raw_wwns,
            "parse_hint": wwn_parse_hint(raw_wwns),
            "searched": searched,
            "matches": matches,
        },
    )


@login_required
def account_details_api(request, project_id):
    try:
        account_details = accounts.build_account_details(project_id)
    except ValueError:
        return JsonResponse({"error": "invalid_project_id"}, status=400)

    return JsonResponse(account_details)


def handle_quota_action(request):
    action = request.POST.get("action")
    form_data = quota_decision_form_data(request.POST)

    quota_request = parse_quota_request_or_warn(request, form_data)

    if quota_request is None:
        return redirect(quotas_retrieve_url(form_data))

    current_quota = quotas.build_quota(
        quota_request.project_id,
        quota_request.openstack_version,
        quota_request.region,
        quota_overrides(request),
    )

    if not quotas.request_is_increase_only(current_quota, quota_request):
        messages.error(request, "Cet outil accepte uniquement les augmentations de quota.")
        return redirect(quotas_retrieve_url(form_data))

    if not quotas.request_has_change(current_quota, quota_request):
        messages.info(request, "Aucun changement de quota a appliquer.")
        return redirect(quotas_retrieve_url(form_data))

    if action == "apply":
        overrides = quotas.apply_request(quota_overrides(request), current_quota, quota_request)
        request.session["quota_overrides"] = overrides
        messages.success(request, "Quota applique pour ce projet.")

    return redirect(quotas_retrieve_url(form_data))


def handle_volume_action(request):
    action = request.POST.get("action")
    openstack_version = selected_openstack_version(
        request.POST.get("openstack_version"),
        openstack_versions_config(),
    )
    region = selected_region(request.POST.get("region"), openstack_regions())
    raw_ids = request.POST.get("ids", "")
    selected_ids = request.POST.getlist("selected_ids")

    if action in {"reset", "bulk_reset"}:
        mark_reset(request, openstack_version, region, selected_ids)
        messages.success(request, f"{len(selected_ids)} volume(s) reinitialise(s) vers available.")

    if action in {"delete", "bulk_delete"}:
        mark_deleted(request, openstack_version, region, selected_ids)
        messages.success(request, f"{len(selected_ids)} volume(s) supprime(s).")

    return redirect(volumes_url(openstack_version, region, raw_ids))


def build_quota_context(request):
    form_data = quota_retrieve_form_data(request.GET)
    project_lookup = parse_project_lookup_or_none(form_data)
    current_quota = None
    rows = []
    searched = "project_id" in request.GET

    if project_lookup:
        current_quota = quotas.build_quota(
            project_lookup["project_id"],
            project_lookup["openstack_version"],
            project_lookup["region"],
            quota_overrides(request),
        )
        rows = quotas.quota_rows(current_quota)
    elif searched:
        messages.error(request, "Project ID invalide. Le Project ID doit etre un UUID.")

    return {
        "openstack_versions": openstack_versions_config(),
        "regions": openstack_regions(),
        "form": form_data,
        "searched": searched,
        "current_quota": current_quota,
        "quota_rows": rows,
    }


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


def parse_quota_request_or_warn(request, form_data):
    quota_request = parse_quota_request_or_none(form_data)

    if quota_request is None:
        messages.error(request, "Project ID ou quota invalide. Le Project ID doit etre un UUID.")

    return quota_request


def quotas_retrieve_url(form_data):
    query = {
        "project_id": form_data["project_id"],
        "openstack_version": form_data["openstack_version"],
        "region": form_data["region"],
    }

    return f"{reverse('quotas')}?{urlencode(query)}"


def quota_overrides(request):
    return dict(request.session.get("quota_overrides", {}))


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


def build_filter_links(
    request,
    openstack_version,
    region,
    raw_ids,
    volumes,
    selected_statuses,
):
    counts = cinder.status_counts(volumes)
    links = [
        {
            "label": "Tous",
            "status": "",
            "count": len(volumes),
            "active": not selected_statuses,
            "url": volumes_url(openstack_version, region, raw_ids),
            "css_class": "all",
        }
    ]

    for status in cinder.available_statuses(volumes):
        next_statuses = set(selected_statuses)

        if status in next_statuses:
            next_statuses.remove(status)
        else:
            next_statuses.add(status)

        links.append(
            {
                "label": status,
                "status": status,
                "count": counts[status],
                "active": status in selected_statuses or not selected_statuses,
                "url": volumes_url(openstack_version, region, raw_ids, next_statuses),
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


def input_token_count(raw_input):
    return len(raw_input.replace(",", " ").split())


def volumes_url(openstack_version, region, raw_ids, statuses=None):
    query = [
        ("openstack_version", openstack_version),
        ("region", region),
        ("ids", raw_ids),
    ]

    for status in sorted(statuses or []):
        query.append(("status", status))

    return f"{reverse('volumes')}?{urlencode(query)}"


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


def session_set(request, key):
    return set(request.session.get(key, []))
