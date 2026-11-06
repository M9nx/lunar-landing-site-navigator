#!/usr/bin/env python3
"""Seed two API sessions and verify run isolation + CSRF. Run inside the api container."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth_utils import new_csrf_token, sign_session_id  # noqa: E402
from config import get_settings
from database import SessionLocal, init_db
from models import ApiSession, CalculationRun, utcnow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.api_base.rstrip("/")
    settings = get_settings()
    init_db()

    def seed(login: str, gid: int) -> tuple[str, str, str]:
        sid = str(uuid.uuid4())
        csrf = new_csrf_token()
        with SessionLocal() as db:
            db.add(
                ApiSession(
                    id=sid,
                    user_github_id=gid,
                    user_login=login,
                    csrf_token=csrf,
                    created_at=utcnow(),
                    last_seen_at=utcnow(),
                )
            )
            run = CalculationRun(
                user_github_id=gid,
                user_login=login,
                status="rejected_not_ready",
                inputs={"probe": login},
            )
            db.add(run)
            db.commit()
            db.refresh(run)
        return sign_session_id(sid), csrf, run.id

    cookie_a, csrf_a, run_a = seed("verify-user-a", 900001)
    cookie_b, _, _ = seed("verify-user-b", 900002)
    cookie_name = settings["session_cookie_name"]

    with httpx.Client(base_url=base, timeout=15.0) as client:
        r = client.get("/runs", cookies={cookie_name: cookie_a})
        r.raise_for_status()
        runs_a = r.json()["runs"]
        if not runs_a or runs_a[0]["inputs"].get("probe") != "verify-user-a":
            print("User A should see their run", file=sys.stderr)
            return 1

        r = client.get("/runs", cookies={cookie_name: cookie_b})
        r.raise_for_status()
        for item in r.json()["runs"]:
            if item["inputs"].get("probe") == "verify-user-a":
                print("User B must not see User A runs", file=sys.stderr)
                return 1

        r = client.get(f"/runs/{run_a}", cookies={cookie_name: cookie_b})
        if r.status_code != 404:
            print(f"User B fetch of A run expected 404 got {r.status_code}", file=sys.stderr)
            return 1

        r = client.post(
            "/runs",
            cookies={cookie_name: cookie_a},
            headers={"Content-Type": "application/json"},
            json={"inputs": {"note": "no csrf"}},
        )
        if r.status_code != 403:
            print(f"POST /runs without CSRF expected 403 got {r.status_code}", file=sys.stderr)
            return 1

        r = client.post(
            "/runs",
            cookies={cookie_name: cookie_a},
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_a},
            json={"inputs": {"note": "with csrf"}},
        )
        if r.status_code != 200:
            print(f"POST /runs with CSRF failed: {r.status_code} {r.text}", file=sys.stderr)
            return 1

    print(json.dumps({"status": "ok", "api_base": base}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
