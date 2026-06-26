from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .build_info import get_build_info
from .camera_service import CameraService
from .config import ConfigStore
from .models import AppConfig


def create_app() -> FastAPI:
    build_info = get_build_info()
    app = FastAPI(title="CM4 V3Link Camera Control Tool", version=build_info.label)
    base_dir = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(base_dir / "templates"))
    static_dir = base_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    service = CameraService(config_store=ConfigStore(), build_info=build_info)
    app.state.service = service
    app.state.build_info = build_info

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": "CM4 V3Link Camera Control Tool",
                "build": build_info.to_dict(),
            },
        )

    @app.get("/api/status")
    def api_status() -> dict:
        return {**service.get_status(), "build": build_info.to_dict()}

    @app.get("/api/cameras")
    def api_cameras() -> dict:
        return {**service.get_status(), "build": build_info.to_dict()}

    @app.get("/api/cameras/{slot}")
    def api_camera(slot: str) -> dict:
        try:
            return service.get_camera(slot).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown camera slot.") from exc

    @app.post("/api/cameras/{slot}/apply")
    def api_camera_apply(slot: str) -> dict:
        try:
            return service.apply_slot(slot).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown camera slot.") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/cameras/{slot}/snapshot")
    def api_camera_snapshot(slot: str) -> Response:
        try:
            snapshot = service.capture_snapshot(slot)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown camera slot.") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if snapshot.bytes_data is not None:
            return Response(content=snapshot.bytes_data, media_type=snapshot.content_type)
        if snapshot.path is not None:
            data = snapshot.path.read_bytes()
            try:
                snapshot.path.unlink(missing_ok=True)
            except Exception:
                pass
            return Response(content=data, media_type=snapshot.content_type)
        raise HTTPException(status_code=500, detail="Snapshot failed.")

    @app.get("/api/cameras/{slot}/preview/frame")
    def api_camera_preview_frame(slot: str) -> Response:
        try:
            frame = service.preview_frame_bytes(slot)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown camera slot.") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return Response(content=frame, media_type="image/jpeg")

    @app.post("/api/cameras/{slot}/preview/start")
    def api_preview_start(slot: str) -> dict:
        try:
            return service.start_preview(slot).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown camera slot.") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/cameras/{slot}/preview/stop")
    def api_preview_stop(slot: str) -> dict:
        try:
            return service.stop_preview(slot).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown camera slot.") from exc

    @app.get("/api/config")
    def api_get_config() -> dict:
        return service.get_config().to_dict()

    @app.post("/api/config")
    async def api_save_config(payload: dict) -> dict:
        try:
            config = AppConfig.from_dict(payload)
            return service.save_config(config).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/cameras/{slot}/settings")
    async def api_update_settings(slot: str, payload: dict) -> dict:
        try:
            return service.update_slot_settings(slot, payload).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown camera slot.") from exc

    @app.get("/api/logs")
    def api_logs() -> dict:
        return {"entries": service.recent_logs()}

    @app.get("/api/version")
    def api_version() -> dict:
        return build_info.to_dict()

    @app.get("/api/health")
    def api_health() -> dict:
        return service.health()

    return app


app = create_app()
