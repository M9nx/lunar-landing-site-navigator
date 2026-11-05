# Lunar Landing Site Navigator

Central workspace for our NASA Space Apps 2026 challenge research, prototype, evaluation, and presentation materials.

**Challenge:** [Lunar Landing Site Navigator](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/)

## Project status

We are in the research and prototype-planning stage. Current working understanding: help users compare lunar landing sites and dates by visualizing the Sun and Earth relative to the local horizon, to examine sunlight and direct-to-Earth communication opportunities.

The research has identified LOLA topography and visibility products as promising lunar data sources and JPL NAIF SPICE as a candidate for date-specific geometry. The calculation pipeline and accuracy have **not** yet been validated.

## Repository map

- [Research draft](docs/RESEARCH_DRAFT.md) — challenge framing, definitions, and current data assessment
- [Sources](docs/SOURCES.md) — annotated source register and relevance decisions
- [Team research brief](docs/TEAM_BRIEF.md) — identical workflow and deliverables for each member
- [Benchmark plan](docs/BENCHMARK_PLAN.md) — proposed accuracy, usability, and runtime measures
- [Project page](docs/index.html) — GitHub Pages landing page
- [Prototype](docs/prototype/index.html) — interactive UI demonstrator using clearly labeled synthetic data
- `.github/workflows/deploy-pages.yml` — GitHub Pages deployment workflow

## Run the prototype locally

Open `docs/prototype/index.html` in a browser. It is a static demo and has no package installation requirement.

> **Scientific status:** Prototype values are synthetic and demonstrate interaction only. They are not NASA measurements, ephemeris results, site recommendations, or validated illumination/communications predictions.

## GitHub Pages

In the repository, open **Settings → Pages**, choose **GitHub Actions** as the build and deployment source, and save. The workflow publishes the `docs/` directory. The site URL will be:

`https://m9nx.github.io/lunar-landing-site-navigator/`

## Data policy

Do not commit large mission-data archives. Record authoritative download links, product identifiers, versions, coordinate frames, resolution, and citation requirements in the research notes. Keep sample data small and clearly identify synthetic or derived content.

## Working principles

1. Separate challenge requirements from our design choices.
2. Cite claims and dataset documentation at the point of use.
3. Label assumptions, estimates, and synthetic values.
4. Keep calculations reproducible: record inputs, time scale, reference frame, kernels, data versions, and processing steps.
5. Do not describe visibility as guaranteed power or a guaranteed radio link.
