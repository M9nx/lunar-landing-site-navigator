# Local data-science workspace

The optional JupyterLab container is intended for private analysis of mission files and reproducible experiments. The research image includes Python, NumPy, pandas, Matplotlib, SpiceyPy, rasterio, Fiona, Shapely, and pyproj.

Start it only on your own machine:

1. Copy `.env.example` to `.env`.
2. Replace `JUPYTER_TOKEN` with a long random value.
3. Run `docker compose --profile research up --build`.
4. Open `http://127.0.0.1:8888` and enter the token.
5. Keep notebooks in `research/notebooks/`; source mission data from the documented provider and store it under `data/`. Downloaded products are gitignored.

`research/notebooks/01_site04_data_audit.ipynb` inspects the NASA PGDA Site04 (Shackleton) LOLA 5 m/pix GeoTIFFs and ROI shapefile. It records native projected coordinates and sampled raster values only. It does not calculate Sun or Earth geometry and does not recommend a landing site.

The notebook port is bound to loopback and is not routed through the public API tunnel. Do not expose JupyterLab to the public internet.
