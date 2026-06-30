from __future__ import annotations

import time
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    venv_python = repo_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        print("update failed: .venv/bin/python not found", file=sys.stderr)
        return 2

    try:
        print("update: stopping healthcheck timer")
        run(["sudo", "systemctl", "stop", "cm4-v3link-healthcheck.timer"], cwd=repo_root)
        print("update: pulling latest code")
        run(["git", "pull"], cwd=repo_root)
        print("update: reinstalling package")
        run([str(venv_python), "-m", "pip", "install", "-e", str(repo_root)], cwd=repo_root)
        print("update: restarting service")
        run(["sudo", "systemctl", "restart", "cm4-v3link"], cwd=repo_root)

        print("update: waiting for service to become active")
        for _ in range(30):
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", "cm4-v3link"],
                cwd=repo_root,
            )
            if result.returncode == 0:
                break
            time.sleep(1)
        else:
            print("update failed: cm4-v3link did not become active", file=sys.stderr)
            return 2

        print("update: restarting healthcheck timer")
        run(["sudo", "systemctl", "start", "cm4-v3link-healthcheck.timer"], cwd=repo_root)
    except subprocess.CalledProcessError as exc:
        print(f"update failed: {exc}", file=sys.stderr)
        return 2

    print("update complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
