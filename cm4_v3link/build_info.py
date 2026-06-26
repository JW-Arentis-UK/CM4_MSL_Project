from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 is not supported.
    tomllib = None  # type: ignore[assignment]


@dataclass(slots=True)
class BuildInfo:
    package_version: str
    git_sha: str

    @property
    def label(self) -> str:
        return f"v{self.package_version}+{self.git_sha}"

    def to_dict(self) -> dict[str, str]:
        return {
            "package_version": self.package_version,
            "git_sha": self.git_sha,
            "label": self.label,
        }


def _git_sha() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        return sha or "unknown"
    except Exception:
        return "unknown"


def get_build_info() -> BuildInfo:
    repo_root = Path(__file__).resolve().parent.parent
    package_ver = "0.1.0"
    pyproject = repo_root / "pyproject.toml"
    if tomllib is not None and pyproject.exists():
        try:
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            package_ver = str(data.get("project", {}).get("version", package_ver))
        except Exception:
            pass
    return BuildInfo(package_version=package_ver, git_sha=_git_sha())
