from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .camera_backends import BackendSnapshot, CameraBackend, create_backend
from .build_info import BuildInfo, get_build_info
from .config import ConfigStore
from .logging_buffer import LogBuffer
from .models import AppConfig, CameraRuntimeState, CameraSettings, DetectedCamera, utc_now


class CameraService:
    def __init__(
        self,
        config_store: ConfigStore | None = None,
        backend: CameraBackend | None = None,
        log_buffer: LogBuffer | None = None,
        build_info: BuildInfo | None = None,
    ) -> None:
        self.config_store = config_store or ConfigStore()
        self.backend = backend or create_backend()
        self.log_buffer = log_buffer or LogBuffer()
        self.build_info = build_info or get_build_info()
        self.config = self.config_store.load()
        self.detected: list[DetectedCamera] = []
        self.runtime_overrides: dict[str, dict[str, Any]] = {}
        self._refresh_discovery()
        self._log(
            "info",
            f"Startup complete build={self.build_info.label} backend={self.backend.__class__.__name__} "
            f"config={self.config_store.path}",
        )

    def _log(self, level: str, message: str) -> None:
        self.log_buffer.add(level, message)

    def _slot_order(self) -> list[str]:
        return list(self.config.cameras.keys())

    def _refresh_discovery(self) -> None:
        self.detected = self.backend.discover()

    def _make_state(self, slot: str) -> CameraRuntimeState:
        slot_cfg = self.config.cameras[slot]
        settings = slot_cfg.settings
        detected_index = self._slot_order().index(slot)
        detected_camera = self.detected[detected_index] if detected_index < len(self.detected) else None
        detected = detected_camera is not None
        if not settings.enabled:
            status = "disabled"
            message = "Camera is disabled in config."
        elif detected:
            status = "ready"
            message = "Camera detected and ready."
        else:
            status = "missing"
            message = "No matching camera detected."
        state = CameraRuntimeState(
            slot=slot,
            enabled=settings.enabled,
            detected=detected,
            detected_id=detected_camera.camera_id if detected_camera else None,
            detected_name=detected_camera.name if detected_camera else None,
            status=status,
            message=message,
            previewing=False,
            snapshot_ready=detected and settings.enabled,
            settings=settings,
        )
        override = self.runtime_overrides.get(slot)
        if override:
            state = replace(state, **override)
        return state

    def get_status(self) -> dict[str, Any]:
        self._refresh_discovery()
        return {
            "cameras": [self._make_state(slot).to_dict() for slot in self._slot_order()],
            "detected_cameras": [
                {"camera_id": camera.camera_id, "name": camera.name, "index": camera.index}
                for camera in self.detected
            ],
        }

    def get_camera(self, slot: str) -> CameraRuntimeState:
        self._refresh_discovery()
        if slot not in self.config.cameras:
            raise KeyError(slot)
        return self._make_state(slot)

    def get_config(self) -> AppConfig:
        self._refresh_discovery()
        return self.config

    def save_config(self, config: AppConfig) -> AppConfig:
        self.config = config
        self.config_store.save(config)
        self._refresh_discovery()
        self._log("info", "Configuration saved.")
        return self.config

    def apply_slot(self, slot: str) -> CameraRuntimeState:
        state = self.get_camera(slot)
        if not state.enabled:
            state.last_error = "Camera is disabled."
            self._log("warning", f"{slot}: apply skipped because camera is disabled.")
            return state
        if not state.detected_id:
            state.last_error = "Camera is not detected."
            self._log("warning", f"{slot}: apply skipped because no camera is detected.")
            return state
        self.backend.apply_settings(state.detected_id, state.settings)
        self._log("info", f"{slot}: settings applied.")
        return self.get_camera(slot)

    def start_preview(self, slot: str) -> CameraRuntimeState:
        state = self.get_camera(slot)
        if not state.detected_id:
            raise RuntimeError("Camera is not detected.")
        self.backend.start_preview(state.detected_id, state.settings)
        self.runtime_overrides[slot] = {
            "previewing": True,
            "status": "previewing",
            "message": "Preview active.",
            "last_error": None,
        }
        self._log("info", f"{slot}: preview started.")
        return self._make_state(slot)

    def stop_preview(self, slot: str) -> CameraRuntimeState:
        state = self.get_camera(slot)
        if state.detected_id:
            self.backend.stop_preview(state.detected_id)
        self.runtime_overrides[slot] = {
            "previewing": False,
            "status": state.status,
            "message": "Preview stopped.",
            "last_error": None,
        }
        self._log("info", f"{slot}: preview stopped.")
        return self._make_state(slot)

    def capture_snapshot(self, slot: str) -> BackendSnapshot:
        state = self.get_camera(slot)
        if not state.detected_id:
            raise RuntimeError("Camera is not detected.")
        snapshot = self.backend.capture_snapshot(state.detected_id, state.settings)
        self.runtime_overrides[slot] = {
            "snapshot_ready": True,
            "last_snapshot_at": utc_now(),
            "message": "Snapshot captured.",
            "last_error": None,
        }
        self._log("info", f"{slot}: snapshot captured.")
        return snapshot

    def update_slot_settings(self, slot: str, settings_data: dict[str, Any]) -> CameraRuntimeState:
        if slot not in self.config.cameras:
            raise KeyError(slot)
        current = self.config.cameras[slot]
        updated_settings = CameraSettings.from_dict({**current.settings.to_dict(), **settings_data})
        self.config.cameras[slot] = replace(current, settings=updated_settings)
        self.config_store.save(self.config)
        self._refresh_discovery()
        self._log("info", f"{slot}: settings updated.")
        return self.get_camera(slot)

    def recent_logs(self) -> list[dict[str, str]]:
        return self.log_buffer.as_list()

    def build_summary(self) -> dict[str, str]:
        return self.build_info.to_dict()

    def health(self) -> dict[str, Any]:
        cameras = [self._make_state(slot) for slot in self._slot_order()]
        return {
            "healthy": True,
            "build": self.build_info.to_dict(),
            "backend": self.backend.__class__.__name__,
            "config_path": str(self.config_store.path),
            "detected_count": len(self.detected),
            "camera_statuses": {camera.slot: camera.status for camera in cameras},
        }

    def preview_frame_bytes(self, slot: str) -> bytes:
        snapshot = self.capture_snapshot(slot)
        if snapshot.bytes_data is not None:
            return snapshot.bytes_data
        if snapshot.path is None:
            raise RuntimeError("Snapshot failed.")
        data = Path(snapshot.path).read_bytes()
        try:
            Path(snapshot.path).unlink(missing_ok=True)
        except Exception:
            pass
        return data
