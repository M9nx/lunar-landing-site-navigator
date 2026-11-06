# Team research workspace

## JupyterHub (recommended)

Multi-user JupyterLab runs under the **`hub` Compose profile** with GitHub OAuth (separate from API login—not SSO).

1. Configure `.env` (Hub OAuth app, allowlists, absolute `HOST_SHARED_NOTEBOOKS`, optional `HOST_SHARED_SCRIPTS`, and `HOST_DATA_PATH`).
2. Build and start: `docker compose --profile hub up --build -d`
3. Access via **`https://hub.m9nx.me`** (or your `HUB_PUBLIC_URL`) through HTTPS reverse proxy—not by publishing notebook ports.

Team template notebooks from git are mounted read-only at `~/shared-readonly/` inside each user server; `research/scripts` is mounted separately at `~/shared-scripts/` (not nested under `shared-readonly`, which is read-only and cannot hold a second bind). User work persists in Docker volume `jupyterhub-user-{username}`.

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
- `research/notebooks/05_site04_b5_terrain_horizon.ipynb`

Notebook 03 has been run in JupyterHub for S04-P02 and produced the 24-hour geometric Sun/Earth CSV plus a kernel/run manifest. Notebook 04 was also run for six Sun/Earth × epoch cases; the owner reports B4 passed at approximately 1e-14° maximum error against the 1e-6° criterion. The B4 manifest and CSV remain in the owner's persistent Hub home and are not committed. This cross-check validates angle conversion, not independent ephemeris truth or terrain visibility.


Notebook 05 has a user-reported near-field result for S04-P02: 720/720 coverage probes complete, matching A/B per-bin pixel-centre sample counts, maximum profile difference about 3.6e-15 degrees, median 0 degrees, and `near_field_pass: true`. Method A streams the pixel-centre samples; Method B rescans the same samples per ray, so agreement checks implementation consistency and is not independent validation of the terrain model. Product 90/far-field compatibility remains unverified; raw B5 artifacts remain in the owner's persistent Hub home and are not committed. The manifest keeps `full_B5_pass: false`.

See `docs/BENCHMARK_PLAN.md` for the reported run details and open far-field B5/B6–B7 gates. The Product 90 compatibility, far-field horizon, and B6 comparison procedure is in [FAR_FIELD_B5_B6_PLAN.md](../docs/FAR_FIELD_B5_B6_PLAN.md). Neither notebook recommends landing sites.

See [FRAME_GEOMETRY_VALIDATION.md](../docs/FRAME_GEOMETRY_VALIDATION.md) for the coordinate pipeline, proposed gates, and team work batch.
