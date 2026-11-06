# Team platform operations

Operations guide for the Lunar Landing Site Navigator **team server** (Docker Compose on a host you control). GitHub Pages serves only static files; Hub, API, secrets, and databases run on the server.

## Public URLs (configure before OAuth)

Record these in your server `.env` after DNS/TLS is in place. Example layout for `m9nx.me`:

| Role | Example host | Purpose |
|------|----------------|---------|
| Static site (Pages) | `https://m9nx.me/lunar-landing-site-navigator/` | Team entry; canonical links |
| Static site (alternate) | `https://m9nx.github.io/lunar-landing-site-navigator/` | May also serve Pages during transition |
| API | `https://api.m9nx.me` | FastAPI, GitHub OAuth (API app), run history |
| JupyterHub | `https://hub.m9nx.me` | Research workspace (separate GitHub OAuth app) |

Quick Cloudflare **Quick Tunnels** (`trycloudflare.com`) are for **local dev/demo only**, not production.

## Static site origins vs API CORS

Browsers send CORS `Origin` as **scheme + host + port** (no path). If both `https://m9nx.me` and `https://m9nx.github.io` serve the site, set `ALLOWED_ORIGINS` to both exact origins.

**Same-site vs cross-site (cookies):** `https://m9nx.me` → `https://api.m9nx.me` is cross-origin but **same-site** (`m9nx.me`). `https://m9nx.github.io` → `https://api.m9nx.me` is **cross-site** (third-party cookie risk). Set `SESSION_COOKIE_SAMESITE` in `.env` after choosing hostnames; see [DEPLOYMENT.md](DEPLOYMENT.md).

Hub and API use **separate GitHub OAuth applications** and **separate sessions**—not single sign-on.

## Compose profiles

| Profile | Services | Host bind (default) |
|---------|----------|---------------------|
| `api` | FastAPI + SQLite run DB | `127.0.0.1:8000` |
| `hub` | JupyterHub + DockerSpawner | `127.0.0.1:8001` → Hub |
| `research` | Legacy single-user JupyterLab (dev fallback) | `127.0.0.1:8888` |

Expose Hub/API to the internet only via **HTTPS reverse proxy or managed Cloudflare Tunnel** on the chosen hostnames—not by publishing user notebook ports.

## Backups

| Data | Location (Compose volumes) | Priority |
|------|----------------------------|----------|
| Hub state | `jupyterhub-hub-db` | High |
| User notebooks | `jupyterhub-user-homes` | High |
| Calculation runs | `api-data` (SQLite) | High |
| Mission data | Host `./data/` (gitignored) | Medium (re-downloadable) |

Example backup: run [`scripts/backup-team-data.sh`](../scripts/backup-team-data.sh) on a schedule, or archive volume mountpoints with restic/tar. Document who runs backups and restore drills.

## Full user revocation (required steps)

Prefer JupyterHub admin UI, REST API, or `jupyterhub` CLI—**not** direct SQL except break-glass.

1. Remove GitHub login from `JUPYTERHUB_ALLOWED_USERS` / `APPROVED_GITHUB_USERS`; restart Hub/API.
2. **Stop** all running notebook servers for that user (Hub admin → Stop server).
3. **Delete** Hub user (`DELETE /hub/api/users/{username}` with admin token, or `jupyterhub delete-user <username>`).
4. **Verify** a browser that still had a Hub session cannot use `/hub/home` or `/user/...` (expect login denied / 403).
5. **Delete** all API server-side sessions for that user (`DELETE /admin/sessions/{login}` with `X-Admin-Token`, or SQL break-glass); confirm old API cookie returns 401 on `/auth/me` and `/runs`.
6. Optional: user revokes GitHub OAuth apps at github.com/settings/applications.
7. Home volume / run history retention is a separate policy (archive or delete `jupyterhub-user-homes/<user>`).

## Resource limits

Hub config sets DockerSpawner memory/CPU caps and spawn timeout. Enable optional idle culling in production if needed.

## Offline behavior

GitHub Pages remains available if the team server is down. Hub/API links show unavailable; prototype stays on **synthetic** demo values.

## DockerSpawner privilege boundary

- Docker socket is mounted **only** on the `jupyterhub` service.
- Single-user containers get home volume + read-only mission data only—**no** socket, Hub secrets, or OAuth client secrets in user env.
