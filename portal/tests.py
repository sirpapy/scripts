from types import SimpleNamespace

from django.test import SimpleTestCase

from portal.presenters import build_filter_links


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
