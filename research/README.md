# Local data-science workspace

The optional JupyterLab container is intended for private analysis of mission files and reproducible experiments. It includes Python, NumPy, pandas, Matplotlib, and SpiceyPy as a starting environment.

Start it only on your own machine:

1. Copy `.env.example` to `.env`.
2. Replace `JUPYTER_TOKEN` with a long random value.
3. Run `docker compose --profile research up --build`.
4. Open `http://127.0.0.1:8888` and enter the token.
5. Keep notebooks in `research/notebooks/`; source mission data from the documented provider and store it under `data/`.

The notebook port is bound to loopback and is not routed through the public API tunnel. Do not expose JupyterLab to the public internet. Add geospatial dependencies such as rasterio only after selecting a concrete LOLA product and checking its format and processing needs.
