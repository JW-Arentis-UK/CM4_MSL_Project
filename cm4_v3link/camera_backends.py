from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .models import CameraSettings, DetectedCamera


_PLACEHOLDER_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBAQEA8PEA8PDw8PDw8PDw8PDw8QFREWFhURExMYHSggGBolGxMTITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGhAQGy0lICYtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLv/AABEIAAEAAQMBIgACEQEDEQH/xAAZAAEAAwEBAAAAAAAAAAAAAAAABAUGAwL/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAHfYf/EABkQAAMBAQEAAAAAAAAAAAAAAAABAhEDIf/aAAgBAQABBQLJzJ0nX//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQMBAT8BP//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8BP//Z"
)

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore[assignment]


@dataclass(slots=True)
class BackendSnapshot:
    path: Path | None = None
    bytes_data: bytes | None = None
    content_type: str = "image/jpeg"


class CameraBackend(ABC):
    @abstractmethod
    def discover(self) -> list[DetectedCamera]:
        raise NotImplementedError

    @abstractmethod
    def apply_settings(self, camera_id: str, settings: CameraSettings) -> None:
        raise NotImplementedError

    @abstractmethod
    def start_preview(self, camera_id: str, settings: CameraSettings) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop_preview(self, camera_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def capture_snapshot(self, camera_id: str, settings: CameraSettings) -> BackendSnapshot:
        raise NotImplementedError


class MockCameraBackend(CameraBackend):
    def discover(self) -> list[DetectedCamera]:
        if os.getenv("CM4_V3LINK_FAKE_CAMERA", "").lower() not in {"1", "true", "yes"}:
            return []
        return [DetectedCamera(camera_id="mock-0", name="Mock Camera", index=0)]

    def apply_settings(self, camera_id: str, settings: CameraSettings) -> None:
        return None

    def start_preview(self, camera_id: str, settings: CameraSettings) -> None:
        return None

    def stop_preview(self, camera_id: str) -> None:
        return None

    def capture_snapshot(self, camera_id: str, settings: CameraSettings) -> BackendSnapshot:
        return BackendSnapshot(bytes_data=_PLACEHOLDER_JPEG)


class Picamera2Backend(CameraBackend):
    def __init__(self) -> None:
        from picamera2 import Picamera2  # type: ignore[import-not-found]

        self._picamera2_cls = Picamera2
        self._instances: dict[str, Any] = {}

    def discover(self) -> list[DetectedCamera]:
        try:
            from picamera2 import Picamera2  # type: ignore[import-not-found]
        except Exception:
            return []
        discovered: list[DetectedCamera] = []
        try:
            cameras = Picamera2.global_camera_info()
        except Exception:
            cameras = []
        for index, camera in enumerate(cameras):
            camera_id = str(camera.get("Id") or camera.get("id") or index)
            name = str(camera.get("Model") or camera.get("model") or f"Camera {index}")
            discovered.append(DetectedCamera(camera_id=camera_id, name=name, index=index))
        return discovered

    def _get_camera(self, camera_id: str):
        if camera_id in self._instances:
            return self._instances[camera_id]
        camera = self._picamera2_cls()
        self._instances[camera_id] = camera
        return camera

    def _apply_common_controls(self, camera: Any, settings: CameraSettings) -> None:
        controls: dict[str, Any] = {}
        if settings.exposure == "auto":
            controls["AeEnable"] = True
        if settings.gain == "auto":
            controls["AnalogueGain"] = None
        if settings.ev_compensation is not None:
            controls["ExposureValue"] = settings.ev_compensation
        if settings.brightness is not None:
            controls["Brightness"] = settings.brightness
        if settings.contrast is not None:
            controls["Contrast"] = settings.contrast
        if settings.saturation is not None:
            controls["Saturation"] = settings.saturation
        if settings.sharpness is not None:
            controls["Sharpness"] = settings.sharpness
        if controls:
            camera.set_controls(controls)

    def _array_to_jpeg_bytes(self, array: Any) -> bytes | None:
        if Image is None or np is None:
            return None
        try:
            if array is None:
                return None
            image = Image.fromarray(array)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            elif image.mode == "L":
                image = image.convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90)
            return buffer.getvalue()
        except Exception:
            return None

    def apply_settings(self, camera_id: str, settings: CameraSettings) -> None:
        camera = self._get_camera(camera_id)
        self._apply_common_controls(camera, settings)

    def start_preview(self, camera_id: str, settings: CameraSettings) -> None:
        camera = self._get_camera(camera_id)
        try:
            camera.configure(camera.create_preview_configuration())
        except Exception:
            pass
        self._apply_common_controls(camera, settings)
        try:
            camera.start()
        except Exception:
            pass

    def stop_preview(self, camera_id: str) -> None:
        camera = self._instances.get(camera_id)
        if camera is None:
            return
        try:
            camera.stop()
        except Exception:
            pass

    def capture_snapshot(self, camera_id: str, settings: CameraSettings) -> BackendSnapshot:
        camera = self._get_camera(camera_id)
        self._apply_common_controls(camera, settings)
        try:
            try:
                array = camera.capture_array()
                jpeg_bytes = self._array_to_jpeg_bytes(array)
                if jpeg_bytes is not None:
                    return BackendSnapshot(bytes_data=jpeg_bytes)
            except Exception:
                pass
            with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp_path = Path(tmp.name)
            try:
                camera.capture_file(str(tmp_path))
                return BackendSnapshot(path=tmp_path)
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise
        except Exception:
            return BackendSnapshot(bytes_data=_PLACEHOLDER_JPEG)


def create_backend() -> CameraBackend:
    try:
        return Picamera2Backend()
    except Exception:
        return MockCameraBackend()
