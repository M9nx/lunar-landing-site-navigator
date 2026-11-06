"""JupyterHub config — secrets and allowlists from environment only."""

import importlib.util
import os
from pathlib import Path

_hub_cfg_path = Path(__file__).resolve().parent / "hub_url_config.py"
_spec = importlib.util.spec_from_file_location("hub_url_config", _hub_cfg_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load hub URL config from {_hub_cfg_path}")
_hub_url = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_hub_url)
hub_oauth_callback_url = _hub_url.hub_oauth_callback_url
validate_hub_url_config = _hub_url.validate_hub_url_config

validate_hub_url_config()

if not os.environ.get("HUB_GITHUB_CLIENT_ID", "").strip():
    raise SystemExit(
        "hub_config: HUB_GITHUB_CLIENT_ID is empty — set Hub OAuth app Client ID in .env"
    )
if not os.environ.get("HUB_GITHUB_CLIENT_SECRET", "").strip():
    raise SystemExit(
        "hub_config: HUB_GITHUB_CLIENT_SECRET is empty — generate secret on GitHub Hub OAuth app"
    )

c = get_config()  # noqa: F821

# --- Auth (GitHub OAuth — separate app from FastAPI) ---
c.JupyterHub.authenticator_class = "github"
c.GitHubOAuthenticator.client_id = os.environ["HUB_GITHUB_CLIENT_ID"]
c.GitHubOAuthenticator.client_secret = os.environ["HUB_GITHUB_CLIENT_SECRET"]
c.GitHubOAuthenticator.oauth_callback_url = hub_oauth_callback_url()
c.GitHubOAuthenticator.scope = ["read:user"]

_allowed_users = {
    u.strip()
    for u in os.environ.get("JUPYTERHUB_ALLOWED_USERS", "").split(",")
    if u.strip()
}
if _allowed_users:
    c.Authenticator.allowed_users = _allowed_users

_allowed_orgs = {
    entry.strip()
    for entry in os.environ.get("JUPYTERHUB_ALLOWED_ORGANIZATIONS", "").split(",")
    if entry.strip()
}
if _allowed_orgs:
    c.GitHubOAuthenticator.allowed_organizations = _allowed_orgs
    c.GitHubOAuthenticator.scope = ["read:user", "read:org"]

_admin_users = {
    u.strip()
    for u in os.environ.get("JUPYTERHUB_ADMIN_USERS", "").split(",")
    if u.strip()
}
if _admin_users:
    c.JupyterHub.admin_users = _admin_users

def _memory_limit_bytes(raw: str) -> int:
    value = raw.strip().lower()
    if value.endswith("g"):
        return int(float(value[:-1]) * 1024**3)
    if value.endswith("m"):
        return int(float(value[:-1]) * 1024**2)
    return int(value)


# --- Spawner (Docker; socket only on Hub container — see compose) ---
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"
c.DockerSpawner.image = os.environ["SINGLEUSER_IMAGE"]
c.DockerSpawner.network_name = os.environ.get("JUPYTERHUB_NETWORK_NAME", "lunar-jupyterhub")
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True
c.DockerSpawner.notebook_dir = "/home/jovyan/work"
_volumes = {
    "jupyterhub-user-{username}": "/home/jovyan/work",
}
if os.environ.get("HOST_SHARED_NOTEBOOKS"):
    _volumes[os.environ["HOST_SHARED_NOTEBOOKS"]] = {
        "bind": "/home/jovyan/shared-readonly",
        "mode": "ro",
    }
if os.environ.get("HOST_DATA_PATH"):
    _volumes[os.environ["HOST_DATA_PATH"]] = {
        "bind": "/home/jovyan/data",
        "mode": "ro",
    }
c.DockerSpawner.volumes = _volumes
# DockerSpawner injects JUPYTERHUB_* for jupyterhub-singleuser; do not override with {}.
c.DockerSpawner.args = ["--ServerApp.ip=0.0.0.0"]
c.DockerSpawner.mem_limit = _memory_limit_bytes(
    os.environ.get("SINGLEUSER_MEM_LIMIT", "2g")
)
c.DockerSpawner.cpu_limit = float(os.environ.get("SINGLEUSER_CPU_LIMIT", "2"))
c.Spawner.start_timeout = int(os.environ.get("SPAWNER_START_TIMEOUT", "300"))

# --- Hub ---
c.JupyterHub.bind_url = "http://:8000"
# Hub API must be reachable from spawned containers on the Docker network (not 127.0.0.1 only).
c.JupyterHub.hub_bind_url = "http://0.0.0.0:8081"
c.JupyterHub.hub_connect_ip = os.environ.get("JUPYTERHUB_HUB_CONNECT_IP", "jupyterhub")
c.Spawner.http_timeout = int(os.environ.get("SPAWNER_HTTP_TIMEOUT", "120"))
c.JupyterHub.cookie_secret_file = "/var/lib/jupyterhub/jupyterhub_cookie_secret"
c.JupyterHub.db_url = os.environ.get("JUPYTERHUB_DB_URL", "sqlite:////var/lib/jupyterhub/jupyterhub.sqlite")
c.JupyterHub.cleanup_servers = True

# Optional idle culler (enable in production): run jupyterhub-idle-culler as a Hub service
# and set c.JupyterHub.services — see https://github.com/jupyterhub/jupyterhub-idle-culler
