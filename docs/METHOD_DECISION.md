# Method Decision Note

**Status:** Proposed research direction; not implemented or validated.  
**Updated:** 2026-11-06

## Question

How can the navigator compare a user-selected lunar site and time while accounting for the Sun, Earth, and terrain?

## Evidence checked

### 1. Standard LOLA visibility products are aggregate products

The documented LOLA GDRVIS products provide average solar illumination and average Earth visibility modeled over approximately one lunar precession cycle (~18.6 years). The NASA PGDA page describes these maps as long-term averages and says that more specific site/duration needs can be discussed with the LOLA team.

**Implication:** GDRVIS is appropriate for broad site screening or a long-term aggregate cross-check. Do not use it as if it were the answer for a selected date/time.

References:
- [LOLA GDRVIS product documentation](https://ode.rsl.wustl.edu/mars/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRVIS.htm)
- [NASA PGDA Lunar Polar Illumination](https://pgda.gsfc.nasa.gov/products/69)

### 2. Site-level LOLA terrain products exist

NASA PGDA lists 5 m/pixel DEMs for **Site04 (Shackleton rim)** and **Site23 (Malapert Massif)**. The page also describes slope, measurement-count, elevation-uncertainty, slope-uncertainty, and ROI shapefile products. The GeoTIFFs use south-polar stereographic coordinates in meters and the MOON_ME frame tied to ephemeris DE421.

**Implication:** We have a concrete path to select documented points inside these regions and estimate a terrain skyline. Use the ROI files to find points; do not treat the region name as an exact landing coordinate. Use the product documentation for the MOON_ME/DE421 frame and height above the 1,737,400 m reference sphere; still verify CRS inversion by round trip, plus NoData treatment, effective resolution, and uncertainty before terrain processing.

Reference:
- [NASA PGDA High-Resolution LOLA Topography for Lunar South Pole Sites](https://pgda.gsfc.nasa.gov/products/78)

### 3. SPICE can provide local sky geometry, but it does not solve the terrain problem by itself

JPL NAIF's `azlcpo_c` computes target azimuth/elevation for a constant-position observer and is explicitly suitable for landmarks on an extended body when those landmarks do not have their own SPK trajectories. It uses a local topocentric frame whose vertical axis follows the surface normal.

**Implication:** A SPICE-based route can calculate date-specific geometric Sun/Earth directions at a surface point. We must still verify the kernel set, coordinate transformations, time conversion, reference frame, and apparent-position settings. A geometric elevation is not terrain clearance.

References:
- [JPL NAIF azlcpo_c](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html)
- [JPL NAIF kernel documentation](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/kernel.html)

## Candidate approaches

| Approach | Can answer selected date/time? | Includes terrain? | Best use | Main limitation |
|---|---|---|---|---|
| Display GDRVIS only | No; published maps are long-term averages | Product's modeled terrain assumptions are embedded in the average | Fast candidate-site screening | Cannot produce user-selected time windows |
| SPICE local azimuth/elevation only | Yes, after a verified implementation | No | Validate geometric positions and build the first scientific baseline | A positive angle may still be blocked by nearby terrain |
| SPICE plus LOLA DEM horizon | Yes, after frame alignment and terrain processing | Yes, under the DEM's resolution/coverage | Most direct route to date-specific terrain-aware windows | More implementation work; DEM uncertainty/resolution matter |
| Request/custom precomputed illumination from PGDA | Potentially, for a specified site/time range | Can be modeled from elevation data | Independent comparison or prepared demo cases | Request/availability and turnaround may not fit hackathon timing |

## Recommended staged method

### Stage A — Validate geometric directions

1. Choose one representative point inside each site ROI.
2. Record its original projected coordinates, converted lunar coordinates if needed, reference frame, and elevation.
3. Convert the selected input time to the time scale expected by SPICE using the relevant time kernel.
4. Use a documented SPICE kernel set to calculate Sun and Earth directions relative to the surface point.
5. Transform the vectors into a local topocentric frame and calculate azimuth/elevation.
6. Compare several fixed cases with an independent ephemeris or reference output before displaying results as scientific.

**Stage A output:** date-specific geometric sky positions. Explicitly label them as geometric and not terrain-cleared.

**Current working artifact:** [Site04 SPICE geometric baseline notebook](../research/notebooks/03_site04_spice_geometric_baseline.ipynb) calculates a fixed-point, 24-hour Sun/Earth geometric series and records a kernel checksum manifest. It is a runnable template and has not yet been executed or benchmark-reviewed. See the [frame and geometry validation plan](FRAME_GEOMETRY_VALIDATION.md) for the proposed gates. The notebook's radial spherical normal is a first baseline, not the DEM terrain normal.

### Stage B — Add terrain visibility

1. Load a DEM covering the site and a surrounding area large enough to represent the skyline.
2. Confirm the projection, lunar frame, height units, no-data treatment, and DEM effective resolution.
3. Build a direction-dependent terrain horizon from the DEM.
4. Compare each target's azimuth/elevation with the terrain horizon at that azimuth.
5. Report Sun and Earth as terrain-clear, terrain-blocked, or uncertain/unsupported by the DEM.
6. Quantify how DEM resolution and elevation uncertainty can change visibility near the horizon.

**Stage B output:** modeled terrain-clear sunlight and Earth line-of-sight windows. This is still not a full solar-power estimate or radio link budget.

### Stage C — Use long-term products as an aggregate check

1. Compute average visibility over a time span and sampling scheme compatible with the selected GDRVIS product.
2. Compare only equivalent quantities and overlapping map cells.
3. Record differences in resolution, terrain, solar/Earth disc treatment, model duration, and time sampling.
4. Treat agreement as an aggregate consistency check, not proof that event times are exact.

## Hackathon-feasible implementation boundary

Recommended initial scientific scope:

- Use two documented regions: Site04 and Site23.
- Use a small number of documented points and fixed date/time cases first.
- Validate geometric Sun/Earth positions before attempting terrain ray tracing.
- If terrain processing cannot be validated in time, show geometric positions and mark terrain visibility as unavailable.
- Keep the current synthetic interface separate from scientific calculations until the pipeline has reference checks.

## Decisions still open

- Exact representative points from Site04 and Site23 ROI shapefiles.
- Whether the supplied 5 m DEM or a smaller/faster regional product is practical.
- Actual kernel hashes, successful coverage checks, and UTC-to-ET outputs from the Stage A notebook.
- Surface-normal method: ellipsoid or DEM-derived local normal.
- Terrain horizon algorithm and necessary radius around the point.
- Time sampling interval and event-boundary refinement.
- Independent reference source and acceptance tolerances.
- Whether a PGDA custom illumination product can be requested in time.

## Key interpretation guardrails

- Geometric elevation above zero is not necessarily visibility above the terrain skyline.
- Sun visibility is not the same as generated solar power.
- Earth visibility is not the same as a complete direct-to-Earth radio link.
- GDRVIS long-term averages are not selected-date predictions.
- Synthetic prototype values are not scientific results.
