# Source Register

Use primary mission/archive documentation and scientific publications wherever possible. Record the exact product version and access date for data actually used.

## Challenge and mission context

1. **NASA Space Apps — Lunar Landing Site Navigator challenge**  
   https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/  
   Primary source for the challenge objective and requested user experience.

2. **NASA — Lunar Reconnaissance Orbiter**  
   https://science.nasa.gov/mission/lro/  
   Mission overview. NASA describes LRO data as supporting lunar site selection and notes the relationship between extended sunlight and surface power.

3. **NASA — LRO Science and Data**  
   https://science.nasa.gov/mission/lro/science-and-data/  
   LRO science and data-product context, including LOLA topography.

## Lunar topography and visibility products

4. **PDS Geosciences Node — LRO LOLA archive**  
   https://pds-geosciences.wustl.edu/missions/lro/lola.htm  
   Archive entry point; lists EDR, RDR, RADR, GDR, and other LOLA products. Use its product documentation and Software Interface Specifications for data interpretation.

5. **NASA PGDA — High-Resolution LOLA Topography for Lunar South Pole Sites**  
   https://pgda.gsfc.nasa.gov/products/78  
   Lists named candidate regions including Shackleton rim (Site04) and Malapert Massif (Site23), with 5 m/pixel GeoTIFF products and metadata. Verify current files, ROI, frame, and uncertainties before use.

6. **NASA PGDA — South Pole LOLA DEM Mosaic**  
   https://pgda.gsfc.nasa.gov/products/81  
   Mosaic product description and downloadable files. The documented 5 m/pixel elevation GeoTIFF is large; check whether a reduced-resolution product is more practical.

7. **Lunar Orbital Data Explorer — LOLA GDRVIS**  
   https://ode.rsl.wustl.edu/mars/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRVIS.htm  
   Documents average solar illumination and Earth visibility maps modeled over ~18.6 years. Appropriate for long-term aggregate comparison, not selected-date event windows.

8. **Lunar Orbital Data Explorer — LOLA GDRSKY**  
   https://ode.rsl.wustl.edu/moon/pagehelp/content/missions_instruments/lro/lola/GDR/GDRSKY.htm  
   Documents sky-solid-angle visibility maps. Supporting terrain context; not a date-specific Sun/Earth product.

9. **Lunar Orbital Data Explorer (ODE)**  
   https://ode.rsl.wustl.edu/moon/  
   Search, map, and download interface for lunar mission archives.

## Geometry and ephemeris

10. **JPL NAIF — Generic SPICE kernels**  
    https://naif.jpl.nasa.gov/naif/data_generic.html  
    Entry point for generic SPICE kernels, including ephemerides, planetary constants, and time kernels. Select files based on coverage and provenance.

11. **JPL NAIF — SPICE kernel required reading**  
    https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/kernel.html  
    Explains kernel types and their roles. Relevant types may include SPK (ephemeris), PCK (body constants/orientation), LSK (leap seconds), and FK (frames).

12. **JPL NAIF — azlcpo_c local azimuth/elevation**  
    https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html  
    Defines local topocentric azimuth/elevation and describes use with landmarks on an extended body.

13. **JPL NAIF — sub-solar point**  
    https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/subsol_c.html  
    SPICE routine for calculating the sub-solar point; useful background, but not by itself a complete local sky-elevation workflow.

## Context and limitations

14. **NASA — Shadows near the Moon’s South Pole**  
    https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/  
    NASA visualization and context for low Sun angles and long, terrain-cast shadows.

15. **NASA — Lunar Surface Propagation**  
    https://www.nasa.gov/glenn/glenn-expertise-space-exploration/scan/lunar-surface-propagation/  
    NASA communications context; terrain affects direct-to-Earth radio propagation, so Earth visibility alone is not a complete link assessment.

16. **NASA — Moon base environment: lunar South Pole**  
    https://www.nasa.gov/reference/moonbase-environment/  
    Context on polar lighting, shadows, and operational impacts.

## Initially suggested sources assessed as not directly relevant

17. **NASA Exoplanet Archive**  
    https://exoplanetarchive.ipac.caltech.edu/  
    Primarily exoplanet, stellar-host, and observational datasets; no direct use identified for this lunar surface prototype.

18. **MAST Portal**  
    https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal.html  
    Astronomical telescope archive; no direct use identified for this lunar surface prototype.

## Citation and data-use notes

- Cite the individual product documentation and scientific paper, not only a portal homepage.
- For each downloaded file, record product ID, version/release, filename, access date, projection, coordinate/reference frame, units, resolution, and any scale/offset values.
- Do not commit large data files until licensing, repository size, and team workflow are checked. Prefer documented download instructions and small derived samples.
- Separate directly measured data from modeled products and synthetic demo values.