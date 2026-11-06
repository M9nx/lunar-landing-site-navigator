"""Validate Hub public URL vs GitHub OAuth callback before JupyterHub starts."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def hub_public_url() -> str:
    return os.environ.get("HUB_PUBLIC_URL", "").strip().rstrip("/")


def hub_oauth_callback_url() -> str:
    explicit = os.environ.get("HUB_OAUTH_CALLBACK_URL", "").strip().rstrip("/")
    public = hub_public_url()
    if explicit:
        return explicit
    if not public:
        return ""
    return f"{public}/hub/oauth_callback"


def validate_hub_url_config() -> None:
    public = hub_public_url()
    callback = hub_oauth_callback_url()
    if not public:
        print("hub_config: HUB_PUBLIC_URL is not set", file=sys.stderr)
        sys.exit(1)
    if not callback:
        print("hub_config: could not determine OAuth callback URL", file=sys.stderr)
        sys.exit(1)

    public_host = _hostname(public)
    callback_host = _hostname(callback)
    public_loopback = _is_loopback_host(public_host)
    callback_loopback = _is_loopback_host(callback_host)

    if not public_loopback and callback_loopback:
        print(
            "hub_config: refusing to start — public HUB_PUBLIC_URL with loopback OAuth callback.\n"
            f"  HUB_PUBLIC_URL={public}\n"
            f"  effective HUB_OAUTH_CALLBACK_URL={callback}\n"
            "  Fix: remove a loopback HUB_OAUTH_CALLBACK_URL from compose overrides; set in .env to\n"
            f"  HUB_OAUTH_CALLBACK_URL={public}/hub/oauth_callback (must match GitHub OAuth app).",
            file=sys.stderr,
        )
        sys.exit(1)

    expected_suffix = "/hub/oauth_callback"
    if not callback.endswith(expected_suffix):
        print(
            f"hub_config: OAuth callback must end with {expected_suffix!r}, got {callback!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not public_loopback:
        public_origin = f"{urlparse(public).scheme}://{urlparse(public).netloc}"
        callback_origin = f"{urlparse(callback).scheme}://{urlparse(callback).netloc}"
        if public_origin != callback_origin:
            print(
                "hub_config: HUB_OAUTH_CALLBACK_URL must share scheme and host with HUB_PUBLIC_URL.\n"
                f"  HUB_PUBLIC_URL={public}\n"
                f"  HUB_OAUTH_CALLBACK_URL={callback}",
                file=sys.stderr,
            )
            sys.exit(1)
