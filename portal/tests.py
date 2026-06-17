from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from portal.presenters import build_filter_links
from portal.services import cinder


class VolumeFilterTests(SimpleTestCase):
    def test_deleting_status_is_available_as_filter(self):
        volumes = [
            SimpleNamespace(status="available"),
            SimpleNamespace(status="deleting"),
            SimpleNamespace(status="deleting"),
        ]

        links = build_filter_links(volumes)
        counts = {link["status"]: link["count"] for link in links}

        self.assertEqual(counts[""], 3)
        self.assertEqual(counts["available"], 1)
        self.assertEqual(counts["deleting"], 2)

    def test_unknown_status_is_not_hidden(self):
        volumes = [SimpleNamespace(status="migrating")]

        links = build_filter_links(volumes)

        self.assertEqual(links[-1]["status"], "migrating")
        self.assertEqual(links[-1]["count"], 1)


class VolumeActionTests(TestCase):
    openstack_version = "v1"
    region = "us-east-1"

    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="admin")
        self.client.login(username="admin", password="admin")

    def test_bulk_reset_ignores_in_use_volumes(self):
        in_use_id = volume_id_for_status("in-use")
        error_id = volume_id_for_status("error")

        self.client.post(
            reverse("volumes"),
            {
                "action": "bulk_reset",
                "openstack_version": self.openstack_version,
                "region": self.region,
                "ids": f"{in_use_id} {error_id}",
                "selected_ids": [in_use_id, error_id],
            },
        )

        reset_keys = set(self.client.session.get("reset_volumes", []))

        self.assertNotIn(volume_key(in_use_id), reset_keys)
        self.assertIn(volume_key(error_id), reset_keys)

    def test_bulk_delete_ignores_in_use_volumes(self):
        in_use_id = volume_id_for_status("in-use")
        available_id = volume_id_for_status("available")

        self.client.post(
            reverse("volumes"),
            {
                "action": "bulk_delete",
                "openstack_version": self.openstack_version,
                "region": self.region,
                "ids": f"{in_use_id} {available_id}",
                "selected_ids": [in_use_id, available_id],
            },
        )

        deleted_keys = set(self.client.session.get("deleted_volumes", []))

        self.assertNotIn(volume_key(in_use_id), deleted_keys)
        self.assertIn(volume_key(available_id), deleted_keys)

    def test_posted_ids_must_belong_to_current_search(self):
        searched_id = volume_id_for_status("available")
        injected_id = volume_id_for_status("available", prefix="vol-injected")

        self.client.post(
            reverse("volumes"),
            {
                "action": "bulk_delete",
                "openstack_version": self.openstack_version,
                "region": self.region,
                "ids": searched_id,
                "selected_ids": [searched_id, injected_id],
            },
        )

        deleted_keys = set(self.client.session.get("deleted_volumes", []))

        self.assertIn(volume_key(searched_id), deleted_keys)
        self.assertNotIn(volume_key(injected_id), deleted_keys)


def volume_id_for_status(status, prefix="vol-test"):
    for index in range(1, 500):
        volume_id = f"{prefix}-{index:03d}"
        volume = cinder.build_volume(volume_id, "v1", "us-east-1")

        if volume.status == status:
            return volume_id

    raise AssertionError(f"No test volume found with status {status}")


def volume_key(volume_id):
    return cinder.volume_key(volume_id, "v1", "us-east-1")
