# Research Draft — Lunar Landing Site Navigator

**Status:** Working draft; research and calculation validation are in progress.  
**Last updated:** 2026-11-05

## 1. Challenge framing

The published challenge asks for an intuitive tool that lets mission planners, educators, and the public compare lunar landing sites and dates. It calls for visualizing Sun and Earth positions relative to the horizon to assess power-generation potential and direct-to-Earth communication windows. See the [official challenge page](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/).

### Draft problem statement

Mission planners and other users need a clear way to compare candidate lunar landing sites and dates. The tool should show how the Sun and Earth appear relative to the horizon at each selected site and time, so users can examine potential sunlight availability and direct-to-Earth communication opportunities. This project will research the data and calculations needed to support that comparison, then demonstrate them in a small functional prototype.

### Requirements versus project decisions

| Category | Current interpretation |
|---|---|
| Explicit challenge requirement | Compare lunar landing sites and dates. |
| Explicit challenge requirement | Visualize Sun and Earth positions relative to the local horizon. |
| Intended use | Assess sunlight for power potential and direct-to-Earth communications opportunities. |
| Project decision to make | Which candidate sites, dates, and time range to include. |
| Project decision to make | What calculation method, data, and interface to use. |
| Needs research | Whether and how the model accounts for local terrain blocking the horizon. |
| Needs research | How calculations will be validated against an independent reference. |

## 2. Science and terminology

JPL SPICE documentation defines local elevation as an angle measured relative to the local topocentric horizontal plane; the local vertical axis is aligned with the outward surface normal. See [SPICE azimuth/elevation documentation](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html).

| Term | Working definition |
|---|---|
| Elevation angle | Angle of a target above or below the local horizontal plane. Zero is the geometric horizon. |
| Geometric horizon | Ideal local tangent plane; does not include terrain skyline. |
| Terrain horizon | Direction-dependent skyline formed by surrounding lunar topography. |
| Sunlight availability | Whether direct sunlight reaches the site under a stated horizon model. |
| Earth visibility | Whether there is geometric line of sight to Earth under a stated horizon model. |
| Communication availability | A possible or modeled communications interval; visibility alone does not guarantee a usable radio link. |

### Important limitation

At the lunar poles, the Sun remains very close to the horizon; NASA describes it as never more than about 1.5 degrees above or below the horizon. Distant terrain can cast long shadows. Therefore, a positive elevation relative to a flat geometric horizon is not necessarily proof of terrain-clear sunlight. NASA's [South Pole environment overview](https://www.nasa.gov/reference/moonbase-environment/) and [LRO shadow visualization](https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/) describe these conditions.

Likewise, Earth visibility is not a complete radio link assessment. NASA notes that terrain can affect direct-to-Earth propagation near the lunar south pole: [Lunar Surface Propagation](https://www.nasa.gov/glenn/glenn-expertise-space-exploration/scan/lunar-surface-propagation/).

### Provisional science and scope paragraph

The prototype will represent the Sun’s and Earth’s positions as elevation angles measured from a selected point on the lunar surface. A positive elevation angle means the object is above the geometric local horizon. This geometric result will be treated as a visibility estimate, not proof that sunlight reaches the surface or that a radio link will work. Terrain can block the Sun or Earth, particularly in the lunar polar environment, where the Sun stays close to the horizon. The research will assess whether terrain horizon data can be included. Any prototype result that does not account for terrain will be labeled as a geometric estimate.

## 3. Preliminary data assessment

### Candidate test regions

Two provisional LOLA south-pole regions are being investigated:

- Shackleton rim — Site04
- Malapert Massif — Site23

The NASA Planetary Geodesy Data Archive (PGDA) lists 5 m/pixel LOLA topography products for these and other named south-pole sites. These names identify regions, not exact landing coordinates. We must select documented points or ROIs from the archive before computing site-specific results. See [High-Resolution LOLA Topography for Lunar South Pole Sites](https://pgda.gsfc.nasa.gov/products/78).

### Candidate products

- **LOLA elevation/topography:** Candidate terrain input for constructing or checking a local horizon. Products include elevation, slope, count, and uncertainty information.
- **LOLA GDRVIS:** Contains modeled maps of average solar illumination and average Earth visibility over approximately one lunar precession cycle (~18.6 years). Useful for site screening or long-term comparisons; it does not provide a selected-date forecast. See [product documentation](https://ode.rsl.wustl.edu/mars/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRVIS.htm).
- **LOLA GDRSKY:** A map of the solid angle of sky visible from the lunar surface. Supporting terrain context; not a date-specific Sun/Earth visibility product. See [product documentation](https://ode.rsl.wustl.edu/moon/pagehelp/content/missions_instruments/lro/lola/GDR/GDRSKY.htm).
- **JPL NAIF SPICE:** Candidate tool and kernels for date-specific ephemeris and frame transformations. The exact kernel set and calculation pipeline remain to be selected and validated. See [generic kernels](https://naif.jpl.nasa.gov/naif/data_generic.html) and [kernel documentation](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/kernel.html).
- **Lunar Orbital Data Explorer (ODE):** Archive search, map, and download interface for lunar mission products: https://ode.rsl.wustl.edu/moon/.

The LOLA south-pole products use specific map projections and lunar reference frames. The chosen data and ephemeris must be checked for frame compatibility before combination. Record product identifiers, versions, resolution, coordinate system, time basis, and citations.

### Relevance of the datasets originally suggested

The NASA Exoplanet Archive focuses on exoplanets, host stars, and related observational data. MAST primarily serves astronomical telescope data. No direct role in this lunar surface navigation prototype has been identified. They should be excluded unless a specific use is justified.

## 4. Proposed calculation route — not yet validated

1. Parse a user-selected date/time and document its time standard.
2. Load suitable SPICE kernels for ephemeris, lunar orientation/reference frames, and time conversion.
3. Select a documented point within a candidate region and express it in a compatible lunar frame.
4. Calculate the Sun and Earth directions from that surface location.
5. Transform each direction to a local topocentric frame and calculate azimuth/elevation.
6. If suitable DEM data is available, estimate a terrain horizon and distinguish terrain-clear visibility from geometric visibility.
7. Display the method, assumptions, and limitations with the result.

SPICE supports local azimuth/elevation calculations for targets viewed from landmarks on an extended body, but our exact Moon/site/kernel pipeline must be implemented and checked against a trusted independent reference before presenting results as validated.

## 5. Prototype scope

The current repository demo is a **synthetic UI demonstrator**. Its site and time controls show the planned interaction only; the numbers are generated for interface demonstration and are not ephemeris calculations or lunar measurements.

The target functional flow is:

1. Select two candidate sites.
2. Select a date and a time within the displayed interval.
3. View Sun/Earth elevation and visibility indicators.
4. Compare sites.
5. See clear provenance and model-limit labels.

## 6. Open research questions

- What exact representative coordinates or ROIs should represent Site04 and Site23?
- Which LOLA files cover those ROIs, and what are their sizes, resolution, frame, and vertical uncertainty?
- Which SPICE kernels and routines are sufficient for date-specific Sun/Earth elevation at a lunar surface point?
- How can a terrain horizon be computed efficiently from the selected DEM?
- What independent reference can validate positions and window boundaries?
- What time sampling is adequate, and how will event-crossing times be refined?
- Which benchmark results can be measured during the hackathon?

## 7. References

See the annotated [source register](SOURCES.md).