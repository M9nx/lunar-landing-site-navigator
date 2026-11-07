"""
SIMULATION / PRACTICE: Server-Sent Events stream of replay visibility results.

Does not gate or replace POST /v1/compare. Not validated science.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from simulation.contracts import SiteHorizonCache
from simulation.engine import process_observation
from simulation.replay import generate_replay_sequence, synthetic_obs_to_dict
from simulation.synthetic_ephemeris import DEFAULT_SCENARIO, ScenarioDefinition

router = APIRouter(prefix="/v1/simulation", tags=["simulation"])

STREAM_EVENT_QUEUE_MAX = 128


class CreateSessionBody(BaseModel):
    scenario_id: str | None = Field(default=None, description="Practice scenario id; default builtin")


class ControlBody(BaseModel):
    action: str = Field(..., description="play | pause | resume | step | stop | set_speed | seek")
    speed: float | None = Field(default=None, ge=0.25, le=32.0)
    index: int | None = Field(default=None, ge=0, description="seek target index for replay")


@dataclass
class StreamSession:
    session_id: str
    scenario: ScenarioDefinition
    sequence: list[dict[str, Any]]
    horizon_cache: dict[str, SiteHorizonCache]
    last_seq: dict[str, int | None]
    last_utc: dict[str, datetime | None]
    index: int = 0
    playing: bool = False
    speed: float = 1.0
    invalid_observation_count: int = 0
    subscribers: list[asyncio.Queue[str]] = field(default_factory=list)
    replay_task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_SESSIONS: dict[str, StreamSession] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _scenario_for_id(sid: str | None) -> ScenarioDefinition:
    if sid in (None, "", DEFAULT_SCENARIO.id):
        return DEFAULT_SCENARIO
    raise ValueError("unknown scenario_id")


def _make_session(body: CreateSessionBody) -> StreamSession:
    scenario = _scenario_for_id(body.scenario_id)
    seq_obs = generate_replay_sequence(scenario)
    seq_dicts = [synthetic_obs_to_dict(o) for o in seq_obs]
    horizon_cache = {
        scenario.site_a: SiteHorizonCache.build(scenario.site_a),
        scenario.site_b: SiteHorizonCache.build(scenario.site_b),
    }
    return StreamSession(
        session_id=str(uuid.uuid4()),
        scenario=scenario,
        sequence=seq_dicts,
        horizon_cache=horizon_cache,
        last_seq={scenario.site_a: None, scenario.site_b: None},
        last_utc={scenario.site_a: None, scenario.site_b: None},
    )


async def _broadcast(sess: StreamSession, payload: dict[str, Any]) -> None:
    line = f"data: {json.dumps(payload)}\n\n"
    for q in list(sess.subscribers):
        try:
            q.put_nowait(line)
        except asyncio.QueueFull:
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(line)
            except asyncio.QueueFull:
                pass


def _session_state(sess: StreamSession) -> dict[str, Any]:
    return {
        "playing": sess.playing,
        "index": sess.index,
        "speed": sess.speed,
        "total": len(sess.sequence),
    }


def _health_event(sess: StreamSession) -> dict[str, Any]:
    return {
        "kind": "stream_health",
        "simulation_mode": True,
        "practice_data": True,
        "connection_state": "live" if sess.playing else "paused",
        "invalid_observation_count": sess.invalid_observation_count,
        "session": _session_state(sess),
        "utc": _now_iso(),
    }


async def _emit_one(sess: StreamSession) -> None:
    async with sess.lock:
        if sess.index >= len(sess.sequence):
            await _broadcast(sess, {"kind": "replay_complete", "utc": _now_iso(), "simulation_mode": True})
            sess.playing = False
            return

        obs = sess.sequence[sess.index]
        res, rej = process_observation(
            obs=obs,
            horizon_cache=sess.horizon_cache,
            last_sequence_by_site=sess.last_seq,
            last_utc_by_site=sess.last_utc,
            check_stale_vs_wall_clock=False,
        )
        if res:
            await _broadcast(
                sess,
                {
                    "kind": "visibility_sample",
                    "simulation_mode": True,
                    "practice_data": True,
                    **asdict(res),
                },
            )
        if rej:
            sess.invalid_observation_count += 1
            await _broadcast(sess, {**rej, "simulation_mode": True, "practice_data": True, "utc": _now_iso()})

        sess.index += 1


async def _replay_worker(sess: StreamSession) -> None:
    try:
        while sess.playing and sess.index < len(sess.sequence):
            await _emit_one(sess)
            delay = max(0.02, 0.35 / sess.speed)
            await asyncio.sleep(delay)
    finally:
        sess.replay_task = None
        if sess.index >= len(sess.sequence):
            sess.playing = False
        await _broadcast(sess, _health_event(sess))


def _ensure_replay_task(sess: StreamSession) -> None:
    if sess.playing and sess.replay_task is None:
        loop = asyncio.get_event_loop()
        sess.replay_task = loop.create_task(_replay_worker(sess))


@router.post("/stream/session")
def create_stream_session(body: CreateSessionBody = CreateSessionBody()):
    try:
        sess = _make_session(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _SESSIONS[sess.session_id] = sess
    return {
        "kind": "session_created",
        "session_id": sess.session_id,
        "scenario": {
            "id": sess.scenario.id,
            "label": sess.scenario.label,
            "site_a": sess.scenario.site_a,
            "site_b": sess.scenario.site_b,
            "site_labels": sess.scenario.site_labels,
            "terrain_source": sess.scenario.terrain_source,
            "resolution_note": sess.scenario.resolution_note,
            "iso_date": sess.scenario.iso_date,
            "sample_count": len(sess.sequence),
        },
        "data_contract": {
            "mode": "SIMULATION_PRACTICE",
            "units": "deg",
            "angles_frame": "local_topocentric_clockwise_from_north_geometric_0",
            "centre_ray_only": True,
            "note": "Swap replay for file/HTTP/WebSocket; validate frames explicitly.",
        },
    }


@router.post("/stream/session/{session_id}/control")
async def control_stream_session(session_id: str, body: ControlBody):
    sess = _SESSIONS.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")

    action = body.action.lower()
    if body.speed is not None:
        sess.speed = body.speed

    if action == "play":
        sess.playing = True
        _ensure_replay_task(sess)
    elif action == "pause":
        sess.playing = False
        if sess.replay_task:
            sess.replay_task.cancel()
            sess.replay_task = None
    elif action == "resume":
        sess.playing = True
        _ensure_replay_task(sess)
    elif action == "stop":
        sess.playing = False
        if sess.replay_task:
            sess.replay_task.cancel()
            sess.replay_task = None
        sess.index = 0
        sess.last_seq = {sess.scenario.site_a: None, sess.scenario.site_b: None}
        sess.last_utc = {sess.scenario.site_a: None, sess.scenario.site_b: None}
        sess.invalid_observation_count = 0
    elif action == "step":
        sess.playing = False
        if sess.replay_task:
            sess.replay_task.cancel()
            sess.replay_task = None
        await _emit_one(sess)
    elif action == "seek":
        if body.index is None:
            raise HTTPException(status_code=400, detail="seek requires index")
        if body.index > len(sess.sequence):
            raise HTTPException(status_code=400, detail="index past end")
        sess.playing = False
        if sess.replay_task:
            sess.replay_task.cancel()
            sess.replay_task = None
        sess.index = body.index
        # rewind validation state to be consistent with replay from this index
        sess.last_seq = {sess.scenario.site_a: None, sess.scenario.site_b: None}
        sess.last_utc = {sess.scenario.site_a: None, sess.scenario.site_b: None}
        sess.invalid_observation_count = 0
        for i in range(body.index):
            obs = sess.sequence[i]
            process_observation(
                obs=obs,
                horizon_cache=sess.horizon_cache,
                last_sequence_by_site=sess.last_seq,
                last_utc_by_site=sess.last_utc,
                check_stale_vs_wall_clock=False,
            )
    elif action == "set_speed":
        pass
    else:
        raise HTTPException(status_code=400, detail="invalid action")

    await _broadcast(sess, _health_event(sess))
    return {"ok": True, "state": _session_state(sess)}


@router.get("/stream/session/{session_id}/state")
def stream_session_state(session_id: str):
    sess = _SESSIONS.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "simulation_mode": True,
        "practice_data": True,
        **_session_state(sess),
        "invalid_observation_count": sess.invalid_observation_count,
    }


@router.get("/stream/session/{session_id}/events")
async def stream_events(session_id: str):
    sess = _SESSIONS.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")

    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=STREAM_EVENT_QUEUE_MAX)

    async def gen():
        sess.subscribers.append(queue)
        await queue.put(
            f"data: {json.dumps({'kind': 'connected', 'simulation_mode': True, 'practice_data': True, 'session_id': session_id, **_session_state(sess)})}\n\n"
        )
        await queue.put(f"data: {json.dumps(_health_event(sess))}\n\n")
        _ensure_replay_task(sess)
        try:
            while True:
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield line
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'kind': 'heartbeat', 'utc': _now_iso(), 'simulation_mode': True, 'practice_data': True})}\n\n"
        finally:
            if queue in sess.subscribers:
                sess.subscribers.remove(queue)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
