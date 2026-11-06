# Deployment: Pages + team server

## Architecture

- **GitHub Pages** serves static files from `docs/` (team entry point).
- **Team server** runs Docker Compose: FastAPI (`api` profile), optional **JupyterHub** (`hub` profile), optional legacy single-user Jupyter (`research` profile).
- **Secrets** live only in server `.env`—never in Pages JavaScript or git.

Canonical static URLs (confirm in GitHub Pages settings):

- `https://m9nx.me/lunar-landing-site-navigator/` (custom domain in use)
- `https://m9nx.github.io/lunar-landing-site-navigator/` (default Pages URL)

Production API/Hub hostnames (example—set in `.env` and DNS):

- `https://api.m9nx.me`
- `https://hub.m9nx.me`

See [OPERATIONS.md](OPERATIONS.md) for revocation, backups, CORS origins, and cookie notes.

**Before public DNS:** complete [GO_LIVE_VERIFICATION.md](GO_LIVE_VERIFICATION.md). Build/health smoke tests alone are not sufficient for multi-user safety.

## Prepare the server

```sh
cp .env.example .env
# Fill secrets, allowlists, and public URLs. Never commit .env.
```

## Start the API

```sh
docker compose up --build -d api
```

Check `http://127.0.0.1:8000/health`. Expect `"science_calculations_ready": false` until validated science is enabled via env after benchmark sign-off.

## Start JupyterHub (team research workspace)

Requires Hub GitHub OAuth app, allowlisted users, and Docker on the host.

### Hub GitHub OAuth app (staging / production)

Create a **separate** GitHub OAuth application from the API app. Set in `.env`:

| Variable | Example (staging) |
|----------|-------------------|
| `HUB_PUBLIC_URL` | `https://hub.m9nx.me` |
| `HUB_OAUTH_CALLBACK_URL` | `https://hub.m9nx.me/hub/oauth_callback` |

If `HUB_OAUTH_CALLBACK_URL` is **empty**, JupyterHub derives **`${HUB_PUBLIC_URL}/hub/oauth_callback`**. Do not set a loopback callback in `.env` when `HUB_PUBLIC_URL` is a public HTTPS hostname—Hub refuses to start (see `jupyterhub/hub_url_config.py`).

Register the **same** callback URL on the GitHub OAuth app. The reverse proxy must forward `https://hub.m9nx.me` → `127.0.0.1:8001`.

```sh
docker compose --profile hub up --build -d
```

Hub binds **`127.0.0.1:8001`** locally. Route **`https://hub.m9nx.me`** (or your hostname) via HTTPS reverse proxy or **managed** Cloudflare Tunnel—do not publish single-user notebook ports.

Hub and API use **separate GitHub OAuth apps** and **separate logins** (not SSO).

## Legacy single-user Jupyter (dev fallback)

```sh
docker compose --profile research up --build
```

`http://127.0.0.1:8888` with token from `.env`. Prefer Hub for team work.

## Staging HTTPS (before go-live)

Until `https://api.m9nx.me/health` returns JSON from your server, GitHub Pages will show **Backend unavailable** and API sign-in cannot be tested. On the team host:

1. Start `docker compose up -d api` (and `--profile hub` when testing Hub).
2. Terminate TLS on **`api.m9nx.me`** → `127.0.0.1:8000` and **`hub.m9nx.me`** → `127.0.0.1:8001` (Caddy, nginx, or Cloudflare Tunnel). Do **not** publish `:8888` or per-user notebook ports.
3. Set `API_PUBLIC_URL=https://api.m9nx.me` and API OAuth callback `https://api.m9nx.me/auth/github/callback` on the **API** GitHub OAuth app.
4. Run `./scripts/verify-api-automated.sh` on the host, then complete [GO_LIVE_VERIFICATION.md](GO_LIVE_VERIFICATION.md) over HTTPS.

Prototype geometry stays **synthetic**; a reachable API only enables auth and run-history testing.

## Connect Pages to the API

1. Point DNS/TLS at your API host (or use a managed tunnel to `127.0.0.1:8000`).
2. Set `ALLOWED_ORIGINS` in `.env` to **exact origins** browsers use (`https://m9nx.me`, `https://m9nx.github.io`, plus local dev if needed)—no path suffixes.
3. Update public URLs in `docs/prototype/config.js` (`apiBaseUrl`, `hubBaseUrl`)—hostnames only, no secrets.
4. Deploy Pages from `main` (GitHub Actions).

**Quick Tunnel** (`trycloudflare.com`) is acceptable for **temporary local demos** only; production should use stable hostnames in config.

## CORS, cookies, and CSRF

- API CORS: exact-origin allowlist, `credentials` enabled for authenticated routes.
- Session cookie lives on the **API host**; `SESSION_COOKIE_SAMESITE` depends on static-site vs API layout (`lax` for same-site subdomains; `none` may be needed for `github.io` → `api.m9nx.me`—test browsers).
- Authenticated **writes** require `X-CSRF-Token` from `GET /auth/csrf` after API login.

Never tunnel Jupyter (8888/8001) for public access without Hub OAuth in front.

## Scientific limitation

Health checks and run history do not imply validated lunar geometry. Prototype values stay **SYNTHETIC** until `SCIENCE_CALCULATIONS_READY=true` after team review.
