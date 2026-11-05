# Team Research Assignment

## Purpose

Each team member independently completes the same research and prototype workflow for the NASA Space Apps challenge. The team will compare the submissions using a common rubric and combine the best-supported ideas into one final solution.

Challenge: https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/

## Rules for every submission

- Follow the same deliverable structure below.
- Cite factual claims close to where they appear.
- Prefer NASA/PDS/JPL primary documentation and peer-reviewed research.
- Mark claims as **source-supported**, **inference**, **assumption**, or **not yet verified** where needed.
- Label synthetic values in demos and figures.
- Record dataset version, coordinates, projection/reference frame, units, time standard, and processing steps.
- Do not describe visibility as guaranteed solar power or a guaranteed communication link.

## Required workflow

### 1. Translate the challenge into requirements
Write a one-paragraph problem statement. Identify the user, the decision they need to make, required inputs and outputs, and what remains outside the prototype scope.

**Submit:** requirements table separating explicit challenge requirements, design decisions, and open research questions.

### 2. Research the geometry and domain terms
Explain local elevation, geometric horizon, terrain horizon, sunlight availability, Earth visibility, and communication availability in plain language. Identify assumptions that change the meaning of the output.

**Submit:** definitions table, method notes, and limitations paragraph.

### 3. Inventory the data and tools
Assess candidate sources, including relevant LOLA/PDS products and any ephemeris/frame tools. Record relevance, exact product, coverage, resolution, coordinate system, format, access route, provenance, and limitations. Explain why any suggested dataset is excluded.

**Submit:** annotated data-source table and references.

### 4. Review related work
Summarize relevant NASA products, research papers, or existing tools. For each, state its method, input data, useful findings, and limitations.

**Submit:** a short related-work table with citations.

### 5. Propose a reproducible method
Describe the full path from site/date input to Sun/Earth elevation and any terrain visibility result. Define time handling, coordinate transforms, horizon model, sampling interval, and output labels.

**Submit:** numbered method or flow diagram and a list of assumptions.

### 6. Set evaluation metrics before measuring
Define accuracy, window timing, usability, and runtime measurements. Specify references, test cases, equations or scoring rules, and what data is still missing.

**Submit:** benchmark plan; do not invent results where no measurements exist.

### 7. Build a small functional demo
Demonstrate the intended user flow: select site/date, inspect Sun/Earth relative to the horizon, and compare at least two options. If the science pipeline is not ready, use conspicuously labeled synthetic values.

**Submit:** runnable demo/link, setup notes, screenshots, and known limitations.

### 8. Prepare a concise individual presentation
Summarize the problem, research, data, method, demo, benchmark plan/results, and limitations. Use Excalidraw for diagrams that clarify the user flow or calculation pipeline.

**Submit:** mini-deck or equivalent visual summary.

## File naming

- `docs/member-submissions/<member-name>/paper.md`
- `docs/member-submissions/<member-name>/sources.md`
- `docs/member-submissions/<member-name>/benchmark-plan.md`
- `prototype/member-demos/<member-name>/`
- `docs/member-submissions/<member-name>/slides-link.md`

Do not overwrite another member’s folder.

## Comparison rubric

Score each category 1–5, provide evidence for each score, then apply the weight.

| Category | Weight |
|---|---:|
| Scientific correctness and clarity about assumptions | 25% |
| Source quality and relevance | 20% |
| Fit to challenge requirements | 15% |
| Reproducibility of method and benchmarks | 15% |
| Demo completeness and usefulness | 15% |
| Clarity of paper and presentation | 10% |

A high score should be supported by citations, reproducible steps, or observed demo behavior—not visual polish alone.