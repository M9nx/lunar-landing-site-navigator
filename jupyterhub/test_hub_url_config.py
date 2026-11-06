"""Run: python test_hub_url_config.py (from jupyterhub/ directory)."""
import os
import unittest
from unittest import mock

from hub_url_config import hub_oauth_callback_url, validate_hub_url_config


class HubUrlConfigTests(unittest.TestCase):
    def test_derives_callback_from_public_url(self):
        with mock.patch.dict(
            os.environ,
            {"HUB_PUBLIC_URL": "https://hub.m9nx.me", "HUB_OAUTH_CALLBACK_URL": ""},
            clear=True,
        ):
            self.assertEqual(
                hub_oauth_callback_url(),
                "https://hub.m9nx.me/hub/oauth_callback",
            )

    def test_rejects_public_public_with_loopback_callback(self):
        with mock.patch.dict(
            os.environ,
            {
                "HUB_PUBLIC_URL": "https://hub.m9nx.me",
                "HUB_OAUTH_CALLBACK_URL": "http://127.0.0.1:8001/hub/oauth_callback",
            },
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                validate_hub_url_config()

    def test_allows_loopback_pair_for_local_dev(self):
        with mock.patch.dict(
            os.environ,
            {
                "HUB_PUBLIC_URL": "http://127.0.0.1:8001",
                "HUB_OAUTH_CALLBACK_URL": "",
            },
            clear=True,
        ):
            validate_hub_url_config()

    def test_rejects_public_http_hub_url(self):
        with mock.patch.dict(
            os.environ,
            {
                "HUB_PUBLIC_URL": "http://hub.m9nx.me",
                "HUB_OAUTH_CALLBACK_URL": "",
            },
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                validate_hub_url_config()


if __name__ == "__main__":
    unittest.main()
