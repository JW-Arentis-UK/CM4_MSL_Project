from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AppConfig


def default_config_path() -> Path:
    env_value = os.getenv("CM4_V3LINK_CONFIG")
    if env_value:
        return Path(env_value)
    return Path("config") / "cameras.json"


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig.default()
            self.save(config)
            return config
        with self.path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(config.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")

