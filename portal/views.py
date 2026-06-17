from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from portal.mock_state import mark_deleted, mark_reset, quota_overrides
from portal.presenters import (
    build_filter_links,
    volume_fields,
    volume_parse_hint,
    volumes_url,
    wwn_parse_hint,
)
from portal.quota_forms import (
    parse_project_lookup_or_none,
    parse_quota_request_or_none,
    quota_decision_form_data,
    quota_retrieve_form_data,
)
from portal.services import accounts, cinder, quotas, wwn
from portal.tool_catalog import TOOL_GROUPS
from portal.view_helpers import (
    openstack_regions,
    openstack_versions_config,
    selected_openstack_version,
    selected_region,
    session_set,
)


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
    ids = cinder.parse_ids(raw_ids)
    searched = "ids" in request.GET

    all_volumes = cinder.build_volumes(
        ids=ids,
        openstack_version=openstack_version,
        region=region,
        deleted_keys=session_set(request, "deleted_volumes"),
        reset_keys=session_set(request, "reset_volumes"),
    )
    displayed_rows = [
        {"volume": volume, "fields": volume_fields(volume)}
        for volume in all_volumes
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
        "displayed_rows": displayed_rows,
        "status_counts": cinder.status_counts(all_volumes),
        "present_statuses": cinder.available_statuses(all_volumes),
        "filter_links": build_filter_links(all_volumes),
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
def account_details_api(_request, project_id):
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
    selected_volumes = selected_volumes_from_post(
        request,
        raw_ids,
        openstack_version,
        region,
    )

    if action in {"reset", "bulk_reset"}:
        resettable_ids = [volume.id for volume in selected_volumes if volume.can_reset]
        ignored_count = len(selected_volumes) - len(resettable_ids)

        if resettable_ids:
            mark_reset(request, openstack_version, region, resettable_ids)
            messages.success(request, f"{len(resettable_ids)} volume(s) reinitialise(s) vers available.")

        warn_ignored_volumes(request, ignored_count)

    if action in {"delete", "bulk_delete"}:
        deletable_ids = [volume.id for volume in selected_volumes if volume.is_deletable]
        ignored_count = len(selected_volumes) - len(deletable_ids)

        if deletable_ids:
            mark_deleted(request, openstack_version, region, deletable_ids)
            messages.success(request, f"{len(deletable_ids)} volume(s) supprime(s).")

        warn_ignored_volumes(request, ignored_count)

    return redirect(volumes_url(openstack_version, region, raw_ids))


def selected_volumes_from_post(request, raw_ids, openstack_version, region):
    searched_ids = set(cinder.parse_ids(raw_ids))
    posted_ids = cinder.parse_ids(" ".join(request.POST.getlist("selected_ids")))
    selected_ids = [volume_id for volume_id in posted_ids if volume_id in searched_ids]

    return cinder.build_volumes(
        ids=selected_ids,
        openstack_version=openstack_version,
        region=region,
        deleted_keys=session_set(request, "deleted_volumes"),
        reset_keys=session_set(request, "reset_volumes"),
    )


def warn_ignored_volumes(request, count):
    if count:
        messages.warning(request, f"{count} volume(s) ignore(s) car non actionnable(s).")


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
