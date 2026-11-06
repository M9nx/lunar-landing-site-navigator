# GitHub OAuth apps (team platform)

Create **two** OAuth applications at [GitHub → Developer settings → OAuth apps](https://github.com/settings/developers). Do not use one app for both Hub and API.

## API application

| Field | Value |
|-------|--------|
| Application name | `Lunar Navigator API` (or similar) |
| Homepage URL | `https://m9nx.me/lunar-landing-site-navigator/` |
| Authorization callback URL | `https://api.m9nx.me/auth/github/callback` |

Copy **Client ID** and generate **Client secret** into server `.env`:

- `API_GITHUB_CLIENT_ID`
- `API_GITHUB_CLIENT_SECRET`

Add allowed GitHub logins (comma-separated, lowercase) to `APPROVED_GITHUB_USERS`.

## JupyterHub application (separate)

| Field | Value |
|-------|--------|
| Application name | `Lunar Navigator Hub` (or similar) |
| Homepage URL | `https://hub.m9nx.me/` |
| Authorization callback URL | `https://hub.m9nx.me/hub/oauth_callback` |

Copy into `.env`:

- `HUB_GITHUB_CLIENT_ID`
- `HUB_GITHUB_CLIENT_SECRET`

Add the same team logins to `JUPYTERHUB_ALLOWED_USERS` (and optional `JUPYTERHUB_ADMIN_USERS`).

## After updating `.env`

```sh
docker compose up -d --force-recreate api
docker compose --profile hub up -d --force-recreate jupyterhub
curl -fsS http://127.0.0.1:8000/health | jq .auth.github_oauth_configured
```

Expect `true` when API OAuth variables are set. Hub login is tested with **GET** `https://hub.m9nx.me/hub/login`.

Never commit `.env` or paste secrets into chat or git.
