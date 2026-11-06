# Team research workspace

## JupyterHub (recommended)

Multi-user JupyterLab runs under the **`hub` Compose profile** with GitHub OAuth (separate from API login—not SSO).

1. Configure `.env` (Hub OAuth app, allowlists, absolute `HOST_SHARED_NOTEBOOKS` / `HOST_DATA_PATH`).
2. Build and start: `docker compose --profile hub up --build -d`
3. Access via **`https://hub.m9nx.me`** (or your `HUB_PUBLIC_URL`) through HTTPS reverse proxy—not by publishing notebook ports.

Team template notebooks from git are mounted read-only at `~/shared-readonly/` inside each user server. User work persists in Docker volume `jupyterhub-user-{username}`.

See [OPERATIONS.md](../docs/OPERATIONS.md) and [DEPLOYMENT.md](../docs/DEPLOYMENT.md).

## Legacy single-user profile (dev fallback)

```sh
docker compose --profile research up --build
```

Open `http://127.0.0.1:8888` with token from `.env`. Do not expose this port publicly.

## Site04 audit notebooks (repo templates)

- `research/notebooks/01_site04_data_audit.ipynb`
- `research/notebooks/02_site04_registration_and_point_selection.ipynb`
- `research/notebooks/03_site04_spice_geometric_baseline.ipynb`
- `research/notebooks/04_site04_azlcpo_b4_validation.ipynb`

Notebook 03 has been run in JupyterHub for S04-P02 and produced the 24-hour geometric Sun/Earth CSV plus a kernel/run manifest. Notebook 04 was also run for six Sun/Earth × epoch cases; the owner reports B4 passed at approximately 1e-14° maximum error against the 1e-6° criterion. The B4 manifest and CSV remain in the owner's persistent Hub home and are not committed. This cross-check validates angle conversion, not independent ephemeris truth or terrain visibility.

See `docs/BENCHMARK_PLAN.md` for the reported run details and open B5–B7 gates. Neither notebook recommends landing sites.

See [FRAME_GEOMETRY_VALIDATION.md](../docs/FRAME_GEOMETRY_VALIDATION.md) for the coordinate pipeline, proposed gates, and team work batch.
