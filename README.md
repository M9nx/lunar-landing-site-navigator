# Lunar Landing Site Navigator

Central workspace for our NASA Space Apps 2026 challenge research, prototype, evaluation, and presentation materials.

**Challenge:** [Lunar Landing Site Navigator](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/)

## Project status

We are in the research and prototype-planning stage. The static interface is deployed on GitHub Pages. A Docker-based API and private data-science workspace are now scaffolded, but no validated lunar calculations are implemented yet.

Current working understanding: help users compare lunar landing sites and dates by visualizing the Sun and Earth relative to the local horizon, to examine sunlight and direct-to-Earth communication opportunities. LOLA topography and illumination products are promising data sources. JPL NAIF SPICE is a candidate for date-specific geometry. The proposed method is documented in [Method decision note](docs/METHOD_DECISION.md), with new product-level findings in the [research update](docs/RESEARCH_UPDATE.md).

## Repository map

- [Research draft](docs/RESEARCH_DRAFT.md) — challenge framing, definitions, and current data assessment
- [Research update](docs/RESEARCH_UPDATE.md) — verified LOLA product inventory, finite-disc caveats, uncertainty notes, and next data-science steps
- [Method decision](docs/METHOD_DECISION.md) — evidence-based route for geometric positions, terrain visibility, and aggregate checks
- [Sources](docs/SOURCES.md) — annotated NASA, PDS, and JPL references
- [Team research brief](docs/TEAM_BRIEF.md) — shared workflow and deliverables for every member
- [Benchmark plan](docs/BENCHMARK_PLAN.md) — proposed accuracy, usability, and runtime measures
- [Deployment guide](docs/DEPLOYMENT.md) — run the Docker API, private notebook environment, and optional HTTPS tunnel
- [Project page](docs/index.html) — GitHub Pages landing page
- [Prototype](docs/prototype/index.html) — interactive UI demo with clearly labeled synthetic values
- `compose.yaml` and `backend/` — local API and optional JupyterLab Docker services

## Run the prototype locally

Open `docs/prototype/index.html` in a browser. It is a static demo and has no package installation requirement.

## Backend and research environment

See [Deployment guide](docs/DEPLOYMENT.md). Docker Compose starts a loopback-only API; the optional JupyterLab service is also local-only and requires a secret token in `.env`. A public HTTPS tunnel is needed for GitHub Pages visitors to reach the API while your machine is awake and online.

The API currently exposes a health check only. It deliberately reports that science calculations are not ready. The prototype's numbers remain synthetic.

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
