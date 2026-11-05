# Research Update — Data Fit and Method Refinements

**Date checked:** 2026-11-05  
**Status:** Verified against NASA / PDS / JPL documentation; computations have not been run.

This note adds specific product-level findings to the [research draft](RESEARCH_DRAFT.md) and [method decision](METHOD_DECISION.md). It should guide dataset selection and API design before any lunar values replace the synthetic prototype.

## 1. Challenge requirements confirmed

The challenge asks users to compare candidate lunar landing sites and dates and see the Sun and Earth relative to the local horizon. Its intended decisions concern potential power generation and direct-to-Earth communication windows. It does not prescribe a data source, exact site coordinates, terrain algorithm, or power/link model. Those remain project decisions.

Source: [Official challenge statement](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/).

## 2. Product-level data findings

### Site-specific LOLA topography

NASA PGDA lists 5 m/pixel GeoTIFF terrain products for both:

- **Site04 — Shackleton rim:** elevation, LOLA count, slope, elevation uncertainty, slope uncertainty, 100 terrain clones, and an explicitly listed `Site04_ROIs.tgz` ROI archive.
- **Site23 — Malapert Massif:** elevation, LOLA count, slope, elevation uncertainty, slope uncertainty, and 100 terrain clones. The current Site23 entry does not list an ROI archive.

The product page says these GeoTIFFs use south-polar stereographic X/Y in metres and the MOON_ME frame tied to DE421. It also reports that roughly 90% of pixels in the 5 m products are interpolated, and that effective resolution varies with LOLA point density. Its stated median RMS uncertainties within the regions of interest are approximately 0.30–0.50 m in elevation and 1.5–2.5° in slope. These values are product context, not guaranteed uncertainty at every pixel.

**Decision:** Site04 is the more straightforward first terrain case because its ROI archive is explicitly linked. Site23 remains a useful comparison region, but do not assume it has a published ROI file. Inspect the current archive and its labels; if no ROI is available, define and document a point from the DEM extent or choose another region with a linked ROI.

The 100 terrain clones provide a potential way to estimate how DEM uncertainty affects a computed skyline and visibility interval. This needs a small feasibility experiment; do not claim a confidence interval until clone processing has been implemented and assessed.

Source: [NASA PGDA, High-Resolution LOLA Topography for Lunar South Pole Sites](https://pgda.gsfc.nasa.gov/products/78).

### Long-term polar illumination and Earth-visibility products

The standard NASA PGDA / PDS polar products offer maps at 240, 120, and 60 m/pixel, depending on latitude coverage. The documented illumination averages span about 18.6 years and use hourly model steps. The product family also includes permanent-shadow, sky-visibility, and Earth-visibility maps. TIF and Cloud-Optimized GeoTIFF variants are linked; NASA cautions that zoomed-out COG views can display averaged overview layers, which should not be used for quantitative pixel extraction.

For illumination, a pixel is counted as sunlit if **any fraction of the solar disc** is visible. Earth visibility likewise counts **any fraction of Earth's disc**. NASA notes that the latter may be slightly optimistic for a radio-link study that depends on specific Deep Space Network stations.

**Decision:** These products are strong for broad candidate screening and compatible aggregate checks. They are not selected-date predictions. When validating an aggregate, match the time span, sampling, surface height, spatial resolution, and disc-visibility definition as closely as possible. A centre-of-disc elevation threshold at zero is not automatically comparable to a product that counts partial-disc visibility.

NASA PGDA says its LOLA data can support point-and-time illumination modeling and invites requests for specified site/duration products. That is a potential expert reference or prepared fallback if a request can be made in time; it is not assumed to be available for the hackathon.

Sources: [NASA PGDA, Lunar Polar Illumination](https://pgda.gsfc.nasa.gov/products/69), [PDS GDRVIS product documentation](https://ode.rsl.wustl.edu/mars/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRVIS.htm), and [NASA Lunar Surface Data Book, 2025 baseline](https://ntrs.nasa.gov/api/citations/20250002845/downloads/M2M-30044%20Lunar%20Surface%20Data%20Book%20Baseline_Final.pdf).

## 3. Geometry method and implementation boundary

JPL NAIF documents `azlcpo_c` for computing target azimuth/elevation as seen from a caller-supplied, fixed-position observer. The routine is described as suitable for surface landmarks on an extended body. Its local topocentric vertical follows the surface normal. This supports the proposed SPICE geometry baseline, but it does not calculate terrain clearance.

Sources: [NAIF azlcpo_c reference](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html) and [NAIF kernel reference](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/kernel.html).

A defensible staged output is:

1. **Geometric baseline:** For a documented surface point and selected time, calculate Sun and Earth centre azimuth/elevation in a stated local frame. Record time conversion, kernels, reference frame, aberration setting, and observer height.
2. **Terrain horizon:** Transform nearby LOLA elevations into a consistent lunar surface geometry, derive a direction-dependent skyline, and compare target elevation with the skyline at matching azimuth. State the DEM radius, effective resolution, observer height, and no-data handling.
3. **Disc-aware visibility (if feasible):** Model the finite solar or Earth disc rather than relying only on its centre. For Earth, label partial-disc geometric visibility separately from a communications link to a particular station.
4. **Uncertainty check:** Repeat terrain calculations on suitable LOLA clones or perturbations and report spread only after validating that the clone ensemble can be processed consistently.
5. **Aggregate check:** Compare with GDRVIS only after aligning the time range and visibility definition.

A local azimuth/range skyline approximation may be useful for a small region, but wide-radius terrain should be mapped into a consistent lunar body-fixed/3D geometry before ray or horizon calculations. Do not treat polar stereographic map X/Y as global Cartesian surface coordinates without accounting for the projection and Moon shape.

## 4. Consequences for benchmarks

Add or clarify these benchmark rules:

- **Geometric angle error:** Compare SPICE output with a genuinely independent calculation/reference and identical time, frame, target centre, local vertical, and aberration convention. Calling the same SPICE routine twice is not independent validation.
- **Terrain-window boundary error:** Define whether a boundary means centre-disc crossing, any-partial-disc visibility, or full-disc visibility. Use the same rule in the implementation and reference.
- **Aggregate illumination difference:** Match the product's long time span and hourly sampling as well as possible; compare compatible pixels and elevation assumptions. Do not use this metric to claim accurate boundaries for one selected date.
- **Terrain uncertainty sensitivity:** Across valid DEM clones or a clearly defined perturbation ensemble, measure changes in horizon angle and window duration. Report the distribution and sampled cases, not just its mean.
- **Runtime and usability:** Report hardware, DEM size, spatial sampling, and whether calculations were cached.

No benchmark results have been measured yet.

## 5. Immediate data-science checklist

Before the first scientific endpoint is added, the researcher should:

- Download only the small required product subset from PGDA/PDS and preserve its labels/README.
- Record the exact file names, access date, projection, reference frame, height units, no-data values, scale/offset, extent, and checksums.
- Inspect whether the Site23 ROI exists outside the page's visible linked products; do not infer its availability.
- Choose one explicit point per site and record how it was selected.
- Confirm that SPICE kernels cover the test epoch and are compatible with the lunar frame used by the DEM.
- Produce one manually reviewable fixed-case output before creating date-window endpoints.

The exoplanet archive and MAST links previously suggested remain unrelated to this surface geometry and LOLA terrain workflow unless a separate, concrete use is identified.
