from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class CameraSettings:
    enabled: bool = True
    name: str = ""
    resolution: str = "1920x1080"
    fps: int = 30
    bitrate: int = 8_000_000
    exposure: str = "auto"
    gain: str = "auto"
    ev_compensation: int = 0
    white_balance: str = "auto"
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    sharpness: float = 1.0
    flip: bool = False
    rotate: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CameraSettings":
        if not data:
            return cls()
        payload = cls().to_dict()
        payload.update({k: v for k, v in data.items() if k in payload})
        return cls(**payload)


@dataclass(slots=True)
class CameraSlotConfig:
    slot: str
    settings: CameraSettings = field(default_factory=CameraSettings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, slot: str, data: dict[str, Any] | None) -> "CameraSlotConfig":
        data = data or {}
        return cls(
            slot=slot,
            settings=CameraSettings.from_dict(data.get("settings") or data),
        )


@dataclass(slots=True)
class AppConfig:
    cameras: dict[str, CameraSlotConfig] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"cameras": {slot: cfg.to_dict() for slot, cfg in self.cameras.items()}}

    @classmethod
    def default(cls) -> "AppConfig":
        return cls(
            cameras={
                "camera_0": CameraSlotConfig(
                    slot="camera_0",
                    settings=CameraSettings(enabled=True, name="Front Camera"),
                ),
                "camera_1": CameraSlotConfig(
                    slot="camera_1",
                    settings=CameraSettings(enabled=False, name="Spare Camera"),
                ),
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AppConfig":
        if not data or "cameras" not in data:
            return cls.default()
        cameras = {
            slot: CameraSlotConfig.from_dict(slot, slot_data)
            for slot, slot_data in data["cameras"].items()
        }
        for slot in ("camera_0", "camera_1"):
            cameras.setdefault(slot, CameraSlotConfig(slot=slot))
        return cls(cameras=cameras)


@dataclass(slots=True)
class DetectedCamera:
    camera_id: str
    name: str
    index: int


@dataclass(slots=True)
class LogEntry:
    timestamp: datetime
    level: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
        }


@dataclass(slots=True)
class CameraRuntimeState:
    slot: str
    enabled: bool
    detected: bool
    detected_id: str | None
    detected_name: str | None
    status: str
    message: str = ""
    previewing: bool = False
    snapshot_ready: bool = False
    last_snapshot_at: datetime | None = None
    last_error: str | None = None
    settings: CameraSettings = field(default_factory=CameraSettings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "enabled": self.enabled,
            "detected": self.detected,
            "detected_id": self.detected_id,
            "detected_name": self.detected_name,
            "status": self.status,
            "message": self.message,
            "previewing": self.previewing,
            "snapshot_ready": self.snapshot_ready,
            "last_snapshot_at": self.last_snapshot_at.isoformat() if self.last_snapshot_at else None,
            "last_error": self.last_error,
            "settings": self.settings.to_dict(),
        }
