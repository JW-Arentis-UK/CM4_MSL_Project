from __future__ import annotations

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
        run(["git", "pull"], cwd=repo_root)
        run([str(venv_python), "-m", "pip", "install", "-e", str(repo_root)], cwd=repo_root)
        run(["sudo", "systemctl", "restart", "cm4-v3link"], cwd=repo_root)
        run(["sudo", "systemctl", "restart", "cm4-v3link-healthcheck.timer"], cwd=repo_root)
    except subprocess.CalledProcessError as exc:
        print(f"update failed: {exc}", file=sys.stderr)
        return 2

    print("update complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

