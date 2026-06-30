from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .models import CameraSettings, DetectedCamera

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]

try:
    from PIL import Image
    from PIL import ImageDraw
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]


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
        return BackendSnapshot(bytes_data=_make_status_jpeg("Mock camera", camera_id, "preview unavailable"))


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

    def _image_to_jpeg_bytes(self, image: Any) -> bytes | None:
        if Image is None or np is None:
            return None
        try:
            if image is None:
                return None
            if hasattr(image, "mode") and image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            elif hasattr(image, "mode") and image.mode == "L":
                image = image.convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90)
            return buffer.getvalue()
        except Exception:
            return None

    def _decorate_jpeg_bytes(self, jpeg_bytes: bytes, title: str, subtitle: str) -> bytes:
        if Image is None or ImageDraw is None:
            return _make_status_jpeg(title, subtitle, "Pillow unavailable")
        try:
            image = Image.open(BytesIO(jpeg_bytes)).convert("RGB")
        except Exception:
            return _make_status_jpeg(title, subtitle, "camera frame unavailable")
        try:
            draw = ImageDraw.Draw(image)
            width, height = image.size
            draw.rectangle((0, 0, width - 1, height - 1), outline=(102, 194, 255), width=8)
            draw.rounded_rectangle((24, 24, min(width - 24, 760), 170), radius=18, fill=(8, 17, 27))
            draw.text((48, 44), title, fill=(236, 244, 255))
            draw.text((48, 94), subtitle, fill=(125, 240, 192))
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90)
            return buffer.getvalue()
        except Exception:
            return _make_status_jpeg(title, subtitle, "camera frame unavailable")

    def apply_settings(self, camera_id: str, settings: CameraSettings) -> None:
        camera = self._get_camera(camera_id)
        self._apply_common_controls(camera, settings)

    def start_preview(self, camera_id: str, settings: CameraSettings) -> None:
        camera = self._get_camera(camera_id)
        try:
            camera.configure(camera.create_preview_configuration(main={"format": "RGB888"}))
        except Exception:
            pass
        self._apply_common_controls(camera, settings)
        try:
            camera.start()
            time.sleep(0.2)
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
            label = f"CM4 V3Link {camera_id}"
            try:
                with camera.captured_request() as request:
                    try:
                        image = request.make_image("main")
                    except Exception:
                        image = request.make_image()
                    jpeg_bytes = self._image_to_jpeg_bytes(image)
                    if jpeg_bytes is not None:
                        return BackendSnapshot(
                            bytes_data=self._decorate_jpeg_bytes(
                                jpeg_bytes,
                                label,
                                "captured_request frame",
                            )
                        )
            except Exception:
                pass
            try:
                array = camera.capture_array("main")
                if array is not None and Image is not None:
                    image = Image.fromarray(array)
                    jpeg_bytes = self._image_to_jpeg_bytes(image)
                    if jpeg_bytes is not None:
                        return BackendSnapshot(
                            bytes_data=self._decorate_jpeg_bytes(
                                jpeg_bytes,
                                label,
                                "capture_array frame",
                            )
                        )
            except Exception:
                pass
            with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp_path = Path(tmp.name)
            try:
                camera.capture_file(str(tmp_path))
                data = tmp_path.read_bytes()
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                return BackendSnapshot(
                    bytes_data=self._decorate_jpeg_bytes(
                        data,
                        label,
                        "capture_file frame",
                    )
                )
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise
        except Exception:
            return BackendSnapshot(
                bytes_data=self._decorate_jpeg_bytes(
                    _make_status_jpeg(f"CM4 V3Link {camera_id}", "preview fallback", "capture failed"),
                    f"CM4 V3Link {camera_id}",
                    "preview fallback image",
                )
            )


def create_backend() -> CameraBackend:
    try:
        return Picamera2Backend()
    except Exception:
        return MockCameraBackend()


def _make_status_jpeg(title: str, subtitle: str, detail: str, size: tuple[int, int] = (1280, 720)) -> bytes:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is required to build status images.")
    image = Image.new("RGB", size, (10, 18, 28))
    draw = ImageDraw.Draw(image)
    width, height = size
    draw.rectangle((0, 0, width - 1, height - 1), outline=(102, 194, 255), width=10)
    draw.rounded_rectangle((48, 48, width - 48, height - 48), radius=28, fill=(16, 28, 42))
    draw.rounded_rectangle((72, 72, width - 72, 220), radius=22, fill=(8, 17, 27))
    draw.text((96, 100), title, fill=(236, 244, 255))
    draw.text((96, 154), subtitle, fill=(125, 240, 192))
    draw.text((96, 620), detail, fill=(153, 171, 194))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()
