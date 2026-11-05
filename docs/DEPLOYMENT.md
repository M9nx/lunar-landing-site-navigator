# Prototype deployment: Pages frontend + Docker API

## What this setup does

- GitHub Pages serves the static interface.
- Docker runs a small FastAPI service on your computer.
- A temporary HTTPS tunnel can make only that API reachable from the Pages site while your computer, Docker, API, and tunnel stay online.
- JupyterLab is an optional local research environment. It stays bound to your own computer and is not routed through the public tunnel.
- The API currently reports service health only. It does not calculate Sun/Earth geometry, terrain visibility, illumination, or communication windows.

## Start the API locally

From the repository root:

```sh
docker compose up --build -d api
```

Check `http://127.0.0.1:8000/health`. The response must include `"status": "ok"` and `"science_calculations_ready": false`.

## Start the private research environment

Copy `.env.example` to `.env`, set a long random `JUPYTER_TOKEN`, then run:

```sh
docker compose --profile research up --build
```

Open `http://127.0.0.1:8888` locally. Do not publish or tunnel this port. Mission data under `data/` is mounted read-only inside both containers.

## Connect the Pages demo

1. Start the API as above.
2. Start a Cloudflare Quick Tunnel to the local API: `cloudflared tunnel --url http://127.0.0.1:8000`.
3. Copy the generated HTTPS `trycloudflare.com` URL.
4. Put that URL into `window.NAVIGATOR_CONFIG.apiBaseUrl` in `docs/prototype/config.js`, without a trailing slash.
5. Commit the config change. GitHub Pages deploys the updated static page.
6. Open the prototype and check its backend status badge.

Quick Tunnel URLs are temporary and may change. Update the config and redeploy when that happens. A stable URL requires a managed tunnel and a domain. The computer must remain awake and online; Docker and the tunnel must keep running. If any stops, the static site remains available but the badge reports the API as unavailable.

## CORS and exposure

The API allows the GitHub Pages origin and local development origins. If using another Pages owner or custom domain, add that exact origin to `ALLOWED_ORIGINS`. The API is bound to loopback on the host; Cloudflare Tunnel makes an outbound connection from your machine. Only the API port is used for this connection. Never forward port 8888 or place secrets in frontend JavaScript or GitHub Pages files.

## Current scientific limitation

A successful health check means only that the API answered. It does not mean scientific inputs are loaded or that computed results are valid. Keep the synthetic demo labels visible until a reproducible pipeline, validated data products, and benchmark evidence replace them.
