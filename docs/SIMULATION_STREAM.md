# Simulation stream (training / practice)

**Status:** SIMULATION and PRACTICE DATA only. Does not use the challenge dataset, validated Site04 frames, or Product 69/90 as operational truth.

## Purpose

Exercise an **incremental** visibility pipeline: observations arrive as a stream; each accepted record produces a **timestamped centre-ray** Sun/Earth state vs a **cached synthetic terrain horizon**. The UI consumes **Server-Sent Events (SSE)** so the browser receives a one-way result stream with ordinary HTTP controls for playback.

## Transport

| Piece | Method | Path |
|--------|--------|------|
| Create session | `POST` | `/v1/simulation/stream/session` |
| Control (play/pause/step/stop/seek/speed) | `POST` | `/v1/simulation/stream/session/{session_id}/control` |
| Poll state | `GET` | `/v1/simulation/stream/session/{session_id}/state` |
| Event stream | `GET` (SSE) | `/v1/simulation/stream/session/{session_id}/events` |

`POST /v1/compare` and `SCIENCE_CALCULATIONS_READY` are **unchanged**.

## Data contract (observation → engine)

Each observation is a JSON object (replay produces this shape):

- `sequence_id` (int, monotonic per site in valid replay)
- `utc` (ISO-8601 UTC)
- `site_id` (`s04p02` \| `malapert` in the default scenario)
- `sun_az_deg`, `sun_el_deg`, `earth_az_deg`, `earth_el_deg` (float, **degrees**)
- `units`: `"deg"`
- `angles_frame`: `local_topocentric_clockwise_from_north_geometric_0` (synthetic local plane; not SPICE)
- `source`: e.g. `replay_synthetic_v1`

**Rejected** records emit `kind: invalid_observation` with a `validity` code. They do **not** emit `visibility_sample` with a clear state.

## Result record (`visibility_sample`)

Includes centre-ray states (`clear` \| `blocked` \| `unknown`), geometric horizon constant `0°` for this toy model, optional terrain margins when terrain is known, and `centre_ray_only: true`.

## Scenario and static terrain

The default scenario precomputes a **3° azimuth bucket** horizon cache per site (see `backend/simulation/contracts.py`). Terrain rules match the teaching model in `docs/prototype/ephemeris.js` (flat Site04; Malapert gap + ridge) — **not** a DEM.

## Replacing the replay source

1. Implement a new generator that yields observation dicts satisfying the contract (or adapt files/HTTP/WebSocket in a new module).
2. Register scenarios in `backend/simulation/synthetic_ephemeris.py`.
3. Wire session creation to your adapter; keep validation in `backend/simulation/engine.py`.

## UI

Static page: [`docs/prototype/stream.html`](prototype/stream.html) (`stream-app.js`). Set **API base** to your running API (e.g. `http://127.0.0.1:8000`). **Create session** opens SSE and enables controls.

## Operations note

Sessions are **in-memory** and bounded (subscriber queues drop coalesced events under pressure). Restarting the API clears sessions.
