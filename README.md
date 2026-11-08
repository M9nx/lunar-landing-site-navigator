# Lunar Landing Site Navigator

Central workspace for our NASA Space Apps 2026 challenge research, prototype, evaluation, and presentation materials.

**Challenge:** [Lunar Landing Site Navigator](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/)

## Project status 

We are in the research and prototype-planning stage. The static interface is deployed on GitHub Pages. A Docker-based team API (GitHub OAuth, run history) and optional JupyterHub research workspace are scaffolded on a loopback Compose stack; validated lunar calculations are not enabled yet.

Current working understanding: help users compare lunar landing sites and dates by visualizing the Sun and Earth relative to the local horizon, to examine sunlight and direct-to-Earth communication opportunities. LOLA topography and illumination products are promising data sources. JPL NAIF SPICE is a candidate for date-specific geometry. The proposed method is documented in [Method decision note](docs/METHOD_DECISION.md), with new product-level findings in the [research update](docs/RESEARCH_UPDATE.md). For how **SPICE**, **rasterio/pyproj**, **Three.js**, and optional **Cesium** divide work, see [Engine calculation pipeline — tool stack](docs/ENGINE_CALCULATION_PIPELINE.md#tool-stack-what-does-what).

## Repository map

- [Research draft](docs/RESEARCH_DRAFT.md) — challenge framing, definitions, and current data assessment
- [Research update](docs/RESEARCH_UPDATE.md) — verified LOLA product inventory, finite-disc caveats, uncertainty notes, and next data-science steps
- [Method decision](docs/METHOD_DECISION.md) — evidence-based route for geometric positions, terrain visibility, and aggregate checks
- [Sources](docs/SOURCES.md) — annotated NASA, PDS, and JPL references
- [Team research brief](docs/TEAM_BRIEF.md) — shared workflow and deliverables for every member
- [Benchmark plan](docs/BENCHMARK_PLAN.md) — proposed accuracy, usability, and runtime measures
- [Deployment guide](docs/DEPLOYMENT.md) — team server Compose profiles (API, Hub, legacy research Jupyter)
- [Operations guide](docs/OPERATIONS.md) — hostnames, CORS, revocation, backups, DockerSpawner boundary
- [Project page](docs/index.html) — GitHub Pages landing page
- [Prototype](docs/prototype/index.html) — interactive UI demo with clearly labeled synthetic values
- [Stream simulation lab](docs/prototype/stream.html) — SIMULATION / PRACTICE SSE replay UI (`/v1/simulation/…`, not gated compare)
- `compose.yaml`, `backend/`, and `jupyterhub/` — API, JupyterHub + DockerSpawner, and legacy single-user Jupyter

## Run the prototype locally

Serve the `docs/` folder over HTTP (e.g. `python3 -m http.server` from `docs/`) and open [`prototype/index.html`](docs/prototype/index.html). The demo loads **Three.js as an ES module** (import map + `ephemeris.js`); opening the file with `file://` may not resolve imports in all browsers. No `npm install` is required.

## Backend and research environment

See [Deployment guide](docs/DEPLOYMENT.md) and [Operations guide](docs/OPERATIONS.md). Docker Compose starts a loopback-only API and optional Hub (`--profile hub`) or legacy research Jupyter. Expose `api.m9nx.me` / `hub.m9nx.me` via HTTPS reverse proxy or managed tunnel—not raw notebook ports.

The API exposes health, GitHub OAuth (separate from Hub), CSRF-protected run history, and a gated `/v1/compare` endpoint. Hub and API sessions are **not** SSO. The prototype UI can sign in to the API and record stub runs; displayed geometry remains **synthetic** until `SCIENCE_CALCULATIONS_READY` is explicitly enabled after benchmarks.

## GitHub Pages

The project page is published at [https://m9nx.github.io/lunar-landing-site-navigator/](https://m9nx.github.io/lunar-landing-site-navigator/). GitHub Actions deploys changes from `docs/` automatically.

## Data policy

Do not commit large mission-data archives. Record authoritative download links, product identifiers, versions, coordinate frames, resolution, and citation requirements in the research notes. Keep sample data small and clearly identify synthetic or derived content.

## Working principles

1. Separate challenge requirements from our design choices.
2. Cite claims and dataset documentation at the point of use.
3. Label assumptions, estimates, and synthetic values.
4. Keep calculations reproducible: record inputs, time scale, reference frame, kernels, data versions, and processing steps.
5. Do not describe visibility as guaranteed power or a guaranteed radio link.
