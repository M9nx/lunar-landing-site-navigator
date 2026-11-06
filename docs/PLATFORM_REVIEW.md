# Platform implementation — review bundle (no secrets)

Use this document for code review **without** sharing `.env`, OAuth client secrets, or admin tokens.

## Git pointer (local workspace)

| Item | Value |
|------|--------|
| Branch | `main` (ahead of last pushed platform work; verify with `git status`) |
| Last published science commits | `ce04e45`, `6c76470` |
| Platform work | Uncommitted changes on `main` — see file list below |

Generate a **sanitized patch** for a reviewer (excludes `.env`):

```sh
cd /path/to/lunar-landing-site-navigator
git add -N backend/ jupyterhub/ scripts/ docs/OPERATIONS.md docs/GO_LIVE_VERIFICATION.md \
  docs/PLATFORM_REVIEW.md docs/assets/js/navigator-config.js
git diff ce04e45 -- . ':(exclude).env' ':(exclude).env.*' > platform-team-hub.patch
```

Share `platform-team-hub.patch` or push a branch and open a PR — **never** attach `.env`.

## Scope summary

| Area | What changed |
|------|----------------|
| **Phase 0–1** | `compose.yaml` profiles (`api`, `hub`, `research`); `jupyterhub/` GitHub OAuth + DockerSpawner; expanded `.env.example` |
| **Phase 2** | `docs/OPERATIONS.md`, `scripts/backup-team-data.sh`, `scripts/restore-team-data.sh`, admin `DELETE /admin/sessions/{login}` |
| **Phase 3** | `backend/main.py`, routers (`auth`, `runs`, `calc`, `admin_ops`), SQLite models, CSRF + CORS credentials |
| **Phase 4** | `docs/index.html`, prototype auth/run UI, `navigator-config.js` |
| **Phase 5** | `backend/calc/` scaffold; `SCIENCE_CALCULATIONS_READY` defaults **false**; `/v1/compare` returns 503 |

## Security-relevant behaviors to review

1. **Allowlists:** Hub `JUPYTERHUB_ALLOWED_USERS`; API `APPROVED_GITHUB_USERS` — empty list denies API login ([`backend/auth_utils.py`](../backend/auth_utils.py)).
2. **Run isolation:** [`backend/routers/runs.py`](../backend/routers/runs.py) filters by `session.user_github_id`.
3. **CSRF:** `POST /runs`, `POST /auth/logout`, `POST /v1/compare` call `verify_csrf`.
4. **CORS:** exact origins from `ALLOWED_ORIGINS`; `allow_credentials=True` ([`backend/main.py`](../backend/main.py)).
5. **Sessions:** signed cookie `navigator_session` ([`backend/auth_utils.py`](../backend/auth_utils.py)); Hub uses separate OAuth app.
6. **Spawner boundary:** Docker socket only on `jupyterhub` service; no secrets in `c.DockerSpawner.environment` ([`jupyterhub/jupyterhub_config.py`](../jupyterhub/jupyterhub_config.py)).

## Verification status

| Check | Automated | Manual (required before public) |
|-------|-----------|----------------------------------|
| Science gate off | `verify-api-automated.sh` | Confirm `.env` on server |
| API CSRF / CORS | `verify-api-automated.sh` | Repeat from live Pages origins |
| API run isolation | `backend/tools/verify_run_isolation.py` (via `verify-api-automated.sh`) | Two real GitHub users in browser |
| Hub allowlist / isolation | — | [GO_LIVE_VERIFICATION.md](GO_LIVE_VERIFICATION.md) §1–2 |
| Persistence | — | §3 |
| Revocation | admin API curl | §5 full runbook |
| Backup restore | restore script | §7 drill |

## Files touched (platform work)

**New:** `backend/auth_utils.py`, `backend/config.py`, `backend/database.py`, `backend/main.py`, `backend/models.py`, `backend/calc/`, `backend/routers/`, `backend/tools/verify_run_isolation.py`, `jupyterhub/`, `scripts/*.sh`, `docs/OPERATIONS.md`, `docs/GO_LIVE_VERIFICATION.md`, `docs/PLATFORM_REVIEW.md`, `docs/assets/js/navigator-config.js`

**Modified:** `compose.yaml`, `backend/Dockerfile`, `backend/app.py`, `backend/requirements.txt`, `.env.example`, `docs/DEPLOYMENT.md`, `docs/index.html`, `docs/prototype/*`, `docs/assets/css/site.css`, `README.md`, `research/README.md`
