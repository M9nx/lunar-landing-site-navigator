# Source Register

Use primary mission/archive documentation and scientific publications wherever possible. For data actually used, record the product version, file name, and access date.

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

## Lunar topography and illumination products

4. **PDS Geosciences Node — LRO LOLA archive**  
   https://pds-geosciences.wustl.edu/missions/lro/lola.htm  
   Archive entry point; lists EDR, RDR, RADR, GDR, and other LOLA products. Use its product documentation and Software Interface Specifications for data interpretation.

5. **NASA PGDA — High-Resolution LOLA Topography for Lunar South Pole Sites**  
   https://pgda.gsfc.nasa.gov/products/78  
   Lists named candidate regions including Shackleton rim (Site04) and Malapert Massif (Site23). The page documents 5 m/pixel GeoTIFF elevation and slope products, count/uncertainty data, and ROI shapefiles. Verify exact files and metadata before use.

6. **NASA PGDA — South Pole LOLA DEM Mosaic**  
   https://pgda.gsfc.nasa.gov/products/81  
   Mosaic product description and downloadable files. The documented 5 m/pixel elevation GeoTIFF is large; check whether a reduced-resolution product is more practical.

7. **NASA PGDA — Lunar Polar Illumination**  
   https://pgda.gsfc.nasa.gov/products/69  
   Describes long-term illumination products and data access. NASA notes that the LOLA team can map illumination at a point and time, while standard public products are typically long-term averages; specific site/duration needs may require a targeted product or discussion with the team.

8. **LOLA GDRVIS — Average solar illumination and Earth visibility**  
   https://ode.rsl.wustl.edu/mars/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRVIS.htm  
   Product documentation for modeled average Sun and Earth visibility over approximately one lunar precession cycle (~18.6 years). Useful for site screening or aggregate consistency checks, not selected-date event windows.

9. **LOLA GDRSKY — Sky visibility**  
   https://ode.rsl.wustl.edu/moon/pagehelp/content/missions_instruments/lro/lola/GDR/GDRSKY.htm  
   Documents maps of the visible sky solid angle. Supporting terrain context; not a date-specific Sun/Earth product.

10. **NASA Lunar Surface Data Book**  
    https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf  
    Describes illumination, Earth-visibility, sky-visibility, and permanent-shadow products and their time/resolution context. It also discusses requesting higher-resolution products for specified time ranges and elevations above the surface.

11. **Lunar Orbital Data Explorer (ODE)**  
    https://ode.rsl.wustl.edu/moon/  
    Search, map, and download interface for lunar mission archives.

## Geometry and ephemeris

12. **JPL NAIF — Generic SPICE kernels**  
    https://naif.jpl.nasa.gov/naif/data_generic.html  
    Entry point for generic SPICE kernels, including ephemerides, planetary constants, and time kernels. Select files based on coverage and provenance.

13. **JPL NAIF — SPICE kernel required reading**  
    https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/kernel.html  
    Explains kernel types and their roles. Relevant types may include SPK (ephemeris), PCK (body constants/orientation), LSK (leap seconds), and FK (frames).

14. **JPL NAIF — azlcpo_c local azimuth/elevation**  
    https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/azlcpo_c.html  
    Defines local topocentric azimuth/elevation and describes use with landmarks on an extended body.

15. **JPL NAIF — sub-solar point**  
    https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/subsol_c.html  
    SPICE routine for calculating the sub-solar point; useful background, but not by itself a complete local sky-elevation workflow.

## Context and limitations

16. **NASA — Shadows near the Moon’s South Pole**  
    https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/  
    NASA visualization and context for low Sun angles and long, terrain-cast shadows.

17. **NASA — Lunar Surface Propagation**  
    https://www.nasa.gov/glenn/glenn-expertise-space-exploration/scan/lunar-surface-propagation/  
    NASA communications context; terrain affects direct-to-Earth radio propagation, so Earth visibility alone is not a complete link assessment.

18. **NASA — Moon base environment: lunar South Pole**  
    https://www.nasa.gov/reference/moonbase-environment/  
    Context on polar lighting, shadows, and operational impacts.

## Initially suggested sources assessed as not directly relevant

19. **NASA Exoplanet Archive**  
    https://exoplanetarchive.ipac.caltech.edu/  
    Primarily exoplanet, stellar-host, and observational datasets; no direct use identified for this lunar surface prototype.

20. **MAST Portal**  
    https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal.html  
    Astronomical telescope archive; no direct use identified for this lunar surface prototype.

## Citation and data-use notes

- Cite individual product documentation and scientific papers, not only portal homepages.
- For every downloaded file, record product ID, version/release, filename, access date, projection, coordinate/reference frame, units, resolution, and scale/offset values.
- Do not commit large mission-data archives until repository size and data-use terms are checked. Prefer documented download instructions and small derived samples.
- Separate measured data from modeled products and synthetic demo values.
