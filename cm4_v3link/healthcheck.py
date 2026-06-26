from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def log_watchdog(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"watchdog failed {timestamp} {message}", file=sys.stderr)


def fetch(url: str) -> dict:
    with urlopen(url, timeout=5) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CM4 V3Link service health.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/health")
    parser.add_argument(
        "--min-detected",
        type=int,
        default=0,
        help="Minimum number of detected cameras required for success.",
    )
    parser.add_argument(
        "--require-camera-0",
        action="store_true",
        help="Fail if camera_0 is not reported as ready, previewing, or snapshot-ready.",
    )
    args = parser.parse_args()

    data = None
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            data = fetch(args.url)
            break
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1)
            else:
                log_watchdog(f"healthcheck fetch error: {exc}")
                return 2

    if data is None:
        log_watchdog(f"healthcheck fetch error: {last_error}")
        return 2

    if not data.get("healthy"):
        log_watchdog("service reported unhealthy")
        return 2

    detected = data.get("detected_cameras") or []
    if len(detected) < args.min_detected:
        log_watchdog(
            f"detected {len(detected)} camera(s), expected at least {args.min_detected}"
        )
        return 2

    if args.require_camera_0:
        statuses = data.get("camera_statuses") or {}
        camera_0_status = statuses.get("camera_0")
        if camera_0_status not in {"ready", "previewing", "snapshot-ready"}:
            log_watchdog(f"camera_0 status is {camera_0_status!r}")
            return 2

    print("healthcheck ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
