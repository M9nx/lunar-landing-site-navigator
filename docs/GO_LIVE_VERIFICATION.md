# Go-live verification (before public Hub/API)

The team platform code is an **implementation baseline**. Docker **build** and **health** smoke checks do **not** prove safe multi-user operation. Complete this checklist on a **staging host** (or production with DNS unpublished) before routing `hub.m9nx.me` and `api.m9nx.me` on the public internet.

**Science gate (unchanged):** keep `SCIENCE_CALCULATIONS_READY=false` in `.env` until benchmark sign-off. The prototype must continue to show **synthetic** geometry only.

## Prerequisites

- `.env` filled on the server (OAuth apps, allowlists, `SESSION_SECRET`, `API_ADMIN_TOKEN`, absolute `HOST_SHARED_NOTEBOOKS`, `HOST_SHARED_SCRIPTS` (defaults to `./research/scripts` if unset), and `HOST_DATA_PATH`).
- HTTPS reverse proxy or managed tunnel terminating TLS on the **same hostnames** used in OAuth callback URLs and `ALLOWED_ORIGINS`.
- Two GitHub accounts for isolation tests: **User A** and **User B** (both on allowlists initially).
- One GitHub account **not** on `JUPYTERHUB_ALLOWED_USERS` / `APPROVED_GITHUB_USERS`.

Automated helpers (no OAuth required):

```sh
./scripts/verify-api-automated.sh http://127.0.0.1:8000
docker compose exec api python tools/verify_run_isolation.py --api-base http://127.0.0.1:8000
```

---

## 1. JupyterHub allowlist

| Step | Action | Pass criteria |
|------|--------|---------------|
| 1.1 | Sign in to Hub as **allowlisted User A** | GitHub OAuth completes; user can open `/hub/home` and **Start** server |
| 1.2 | Open JupyterLab; create `verify-persistence.txt` in home | File visible in Lab file browser |
| 1.3 | Sign in as **non-allowlisted** account | Access denied before spawn (no `/user/...` server) |
| 1.4 | Remove non-allowlisted test from allowlist (if temporarily added) | N/A |

---

## 2. Notebook isolation (Hub)

| Step | Action | Pass criteria |
|------|--------|---------------|
| 2.1 | User A and User B each start a server | Distinct `/user/<login>/` URLs |
| 2.2 | User A creates a notebook or file with a unique name | Only A sees it under A’s tree |
| 2.3 | User B tries to open A’s `/user/<A>/...` URL directly | **403 / not found** — B cannot read A’s server |
| 2.4 | Confirm spawned containers only mount **their** named volume + shared read-only paths | Inspect `docker inspect` on user containers: no other user’s home volume |

---

## 3. Persistence across Hub restart

| Step | Action | Pass criteria |
|------|--------|---------------|
| 3.1 | With User A’s file from §1.2 present | Note path and contents |
| 3.2 | `docker compose --profile hub restart jupyterhub` (or full host reboot) | Hub returns |
| 3.3 | User A starts server again | `verify-persistence.txt` still present with same contents |

User homes live in Docker named volumes `jupyterhub-user-<username>` (created by DockerSpawner).

---

## 4. API run isolation

| Step | Action | Pass criteria |
|------|--------|---------------|
| 4.1 | Run `docker compose exec api python tools/verify_run_isolation.py` | Script exits 0 |
| 4.2 | User A signs in on prototype; **Record stub run** | Run appears in A’s list |
| 4.3 | User B signs in (separate browser profile); lists runs | B does **not** see A’s runs |
| 4.4 | B guesses A’s run UUID in `GET /runs/{id}` | **404** |

Implementation note: list/detail queries filter on `user_github_id` ([`backend/routers/runs.py`](../backend/routers/runs.py)).

---

## 5. Revocation (Hub + API)

Prepare: note User A’s active Hub session and API session (signed in on prototype).

| Step | Action | Pass criteria |
|------|--------|---------------|
| 5.1 | Remove User A from `JUPYTERHUB_ALLOWED_USERS` and `APPROVED_GITHUB_USERS`; restart Hub and API | Services reload env |
| 5.2 | Hub admin: **Stop** A’s server; delete Hub user if policy requires | Server stopped |
| 5.3 | `curl -X DELETE "https://api.<host>/admin/sessions/<login>" -H "X-Admin-Token: <token>"` | `deleted_sessions` ≥ 1 |
| 5.4 | Browser with old Hub cookie: visit `/hub/home` | Cannot use workspace (login denied / no spawn) |
| 5.5 | Same browser: `GET /auth/me` with old API cookie | **401** |
| 5.6 | User A attempts new Hub/API login | **403** / denied (not on allowlist) |

See [OPERATIONS.md](OPERATIONS.md) for the full ordered runbook.

---

## 6. CORS and CSRF from real Pages origins

Run from a machine that can reach the API (replace host and origins):

```sh
export API=https://api.m9nx.me
export ORIGIN=https://m9nx.me

# Preflight (must include Origin and credentials)
curl -sS -D - -o /dev/null -X OPTIONS "$API/runs" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-csrf-token"

# Expect: Access-Control-Allow-Origin: $ORIGIN (exact, not *)
# Expect: Access-Control-Allow-Credentials: true
```

Repeat with `ORIGIN=https://m9nx.github.io` if both Pages URLs are in `ALLOWED_ORIGINS`.

**CSRF:** authenticated `POST /runs` without `X-CSRF-Token` must return **403**; with token from `GET /auth/csrf` must succeed. `./scripts/verify-api-automated.sh` covers this against loopback using seeded sessions.

**Browser check:** open prototype from **production Pages URL** (not `file://`), sign in, record stub run, sign out — no CORS errors in devtools.

---

## 7. Backup and restore drill

| Step | Action | Pass criteria |
|------|--------|---------------|
| 7.1 | `./scripts/backup-team-data.sh /var/backups/lunar-navigator` | Archives created (api-data, hub-db, user homes, optional host `data/`) |
| 7.2 | On a **throwaway** Compose project or stopped stack, `./scripts/restore-team-data.sh <archive-dir> <timestamp>` | See script usage |
| 7.3 | Start Hub; User A’s home file from §3 still present | Restore validated |

Schedule backups only after a successful restore drill.

---

## 8. Public exposure gate

Do **not** point production DNS at Hub/API until **all** sections above pass. Keep Quick Tunnel / dev URLs out of [`docs/prototype/config.js`](../docs/prototype/config.js) for production.

After go-live, re-run §6 from each live Pages origin after any `ALLOWED_ORIGINS` change.
