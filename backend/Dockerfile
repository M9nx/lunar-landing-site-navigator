FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

FROM base AS api
ENV DATABASE_URL=sqlite:////data/navigator.db
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS singleuser
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir jupyterhub jupyterlab numpy pandas matplotlib spiceypy rasterio fiona shapely pyproj
RUN useradd -m -s /bin/bash -u 1000 jovyan \
    && mkdir -p /home/jovyan/work /home/jovyan/shared-readonly /home/jovyan/shared-scripts /home/jovyan/data \
    && chown -R jovyan:jovyan /home/jovyan
USER jovyan
WORKDIR /home/jovyan/work
EXPOSE 8888
CMD ["jupyterhub-singleuser"]

FROM base AS research
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir jupyterlab numpy pandas matplotlib spiceypy rasterio fiona shapely pyproj
WORKDIR /workspace
EXPOSE 8888
CMD ["sh", "-c", "jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --ServerApp.allow_remote_access=True --ServerApp.token=\"$JUPYTER_TOKEN\""]
