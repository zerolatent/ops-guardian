from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .config import Settings, get_settings
from .data_loader import DemoData
from .model_adapters import (
    ModelAdapter,
    ModelAdapterError,
    MockScenarioAdapter,
    OpenAICompatibleAdapter,
)
from .models import CreateRunRequest, RunState
from .runner import ScenarioRunner
from .storage import Storage


def create_app(settings: Settings | None = None, adapter: ModelAdapter | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    demo_data = DemoData(resolved_settings.data_dir)
    storage = Storage(resolved_settings.sqlite_path)
    mock_adapter = adapter or MockScenarioAdapter()
    live_adapter = OpenAICompatibleAdapter(resolved_settings)
    runner = ScenarioRunner(resolved_settings, storage, demo_data, mock_adapter, live_adapter=live_adapter)

    app = FastAPI(title=resolved_settings.app_name, version="0.1.0")
    app.state.runner = runner

    static_dir = Path(__file__).parent / "static"

    def get_runner() -> ScenarioRunner:
        return app.state.runner

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": resolved_settings.app_name}

    @app.get("/", response_class=HTMLResponse)
    def home() -> FileResponse:
        return FileResponse(static_dir / "cockpit.html")

    @app.get("/cockpit", response_class=HTMLResponse)
    def cockpit() -> FileResponse:
        return FileResponse(static_dir / "cockpit.html")

    @app.get("/console", response_class=HTMLResponse)
    def console() -> FileResponse:
        return FileResponse(static_dir / "console.html")

    @app.get("/media/videos/{filename}")
    def video_file(filename: str) -> FileResponse:
        videos_dir = (resolved_settings.data_dir / "videos").resolve()
        path = (videos_dir / filename).resolve()
        if path.suffix.lower() != ".mp4" or videos_dir not in path.parents or not path.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        return FileResponse(path, media_type="video/mp4")

    @app.get("/api/scenarios")
    def list_scenarios(active_runner: ScenarioRunner = Depends(get_runner)) -> list[dict]:
        return active_runner.list_scenarios()

    @app.get("/api/runs")
    def list_runs(active_runner: ScenarioRunner = Depends(get_runner)) -> list[dict]:
        return active_runner.storage.list_runs()

    @app.post("/api/runs")
    def create_run(
        request: CreateRunRequest,
        active_runner: ScenarioRunner = Depends(get_runner),
    ) -> RunState:
        try:
            return active_runner.start_run(request)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/step")
    async def step_run(run_id: str, active_runner: ScenarioRunner = Depends(get_runner)) -> RunState:
        try:
            return await active_runner.step_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ModelAdapterError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/complete")
    async def complete_run(run_id: str, active_runner: ScenarioRunner = Depends(get_runner)) -> RunState:
        try:
            return await active_runner.complete_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ModelAdapterError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, active_runner: ScenarioRunner = Depends(get_runner)) -> RunState:
        try:
            return active_runner.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}/handover")
    def get_handover(run_id: str, active_runner: ScenarioRunner = Depends(get_runner)) -> dict:
        try:
            return active_runner.get_handover(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/reset")
    def reset(active_runner: ScenarioRunner = Depends(get_runner)) -> dict[str, str]:
        return active_runner.reset()

    return app


app = create_app()


def run_dev() -> None:
    uvicorn.run("ops_guardian.app:app", host="127.0.0.1", port=8000, reload=True)
