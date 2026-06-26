from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


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

    try:
        data = fetch(args.url)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        print(f"healthcheck failed: {exc}", file=sys.stderr)
        return 2

    if not data.get("healthy"):
        print("healthcheck failed: service reported unhealthy", file=sys.stderr)
        return 2

    detected = data.get("detected_cameras") or []
    if len(detected) < args.min_detected:
        print(
            f"healthcheck failed: detected {len(detected)} camera(s), expected at least {args.min_detected}",
            file=sys.stderr,
        )
        return 2

    if args.require_camera_0:
        statuses = data.get("camera_statuses") or {}
        camera_0_status = statuses.get("camera_0")
        if camera_0_status not in {"ready", "previewing", "snapshot-ready"}:
            print(
                f"healthcheck failed: camera_0 status is {camera_0_status!r}",
                file=sys.stderr,
            )
            return 2

    print("healthcheck ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

