---
name: lunar-navigator-deployment-host
description: Explains which machine is the Docker host for this repo, how JupyterHub bind-mounts mission data read-only to /home/jovyan/data, and how to resolve HOST_DATA_PATH vs container paths. Use when the user asks where Hub data lives, which VPS or host runs Docker, why touch fails on ~/data, how to add COGs or rasters for notebooks, cloudflared vs containers, or scp/rsync placement for LOLA/Product 90 files.
---

# Lunar Navigator: Docker host and Hub data

## Definitions

- **Docker host:** The machine where `docker compose` runs for this repository (API, JupyterHub, singleuser image). It is not “the Jupyter tab in the browser”; that tab runs **inside** a container on this host.
- **Mission data directory:** On the host, the path set by **`HOST_DATA_PATH`** in `.env` (default from Compose: **`./data`** relative to the repo — i.e. [`data/`](../../../data) at repo root). Git ignores contents under `data/*` except documented exceptions; see [`.gitignore`](../../../.gitignore).
- **Inside the singleuser container:** `HOST_DATA_PATH` is mounted at **`/home/jovyan/data`** as **read-only** (`:ro`). So `touch ~/data/...` or `mkdir` under `~/data` **fails by design**; writes must happen on the **host** at `HOST_DATA_PATH`, or in the user’s writable home (e.g. `~/work`). **`HOST_SHARED_SCRIPTS`** mounts at **`~/shared-scripts`** (not under `~/shared-readonly`, which is already a read-only bind and cannot nest another mount).

## Source of truth in repo

- [`compose.yaml`](../../../compose.yaml): `jupyterhub` service sets `HOST_DATA_PATH` and mounts `${HOST_DATA_PATH}:${HOST_DATA_PATH}:ro` for the Hub service; singleuser containers get the same host path bound to `/home/jovyan/data` (see JupyterHub spawner config under [`jupyterhub/`](../../../jupyterhub)).
- [`docs/OPERATIONS.md`](../../../docs/OPERATIONS.md): team server layout, public URLs, volume/mission data notes.
- [`docs/FAR_FIELD_B5_B6_PLAN.md`](../../../docs/FAR_FIELD_B5_B6_PLAN.md): where to place Product 90 COGs under `data/LOLA_20mpp/` and audit before stacking.

## How the agent should resolve “where do files go?”

1. Prefer reading **`.env`** in the repo for **`HOST_DATA_PATH`**. If unset, Compose defaults to **`./data`** (repo-root `data/`).
2. To confirm a **running** user server, suggest (on the Docker host):

   ```sh
   docker ps --format 'table {{.Names}}\t{{.Image}}'
   docker inspect CONTAINER_NAME --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
   ```

   Find **`-> /home/jovyan/data`**: the **Source** path is where new rasters belong (e.g. `.../data/LOLA_20mpp/`).

3. **Public URLs** (`hub.m9nx.me`, `api.m9nx.me`) are fronted by a tunnel or reverse proxy on the host; they do not change the bind-mount rules.

## Agent reminders

- Do not tell the user to download large rasters **into git**; use `data/` on the host.
- Read-only **`~/data`** does not prevent **reading** files placed on the host; if notebooks do not see new files, suggest refreshing the file browser or restarting the user server after host-side copies.
- **Cursor’s sandbox** may hide `docker` or under-report the host; when diagnosing “which machine,” prefer the user’s SSH session on the Docker host or `docker inspect` output they paste.
