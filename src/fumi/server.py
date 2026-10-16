"""Fumi's local server: the UI and a small JSON API. Routes stay thin and the modules do the work."""

import contextlib
import json
import time
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fumi import auth, envs, security, sender, spec, store
from fumi.events import Broadcaster
from fumi.workspace import Workspace

STATIC = Path(__file__).parent / "static"
MAX_BRANCH_STATE = 2_000_000


class OpenIn(BaseModel):
    path: str


class SendIn(BaseModel):
    env: str
    method: str
    path: str
    query: list[tuple[str, str]] = []
    headers: list[tuple[str, str]] = []
    body: str | None = None
    confirm: str | None = None  # the env's name typed by the user for writes to a protected env


class AuthIn(BaseModel):
    type: Literal["none", "browser", "api_key"] = "none"
    browser: Literal["brave", "chrome", "arc", "edge"] = "brave"
    header: str = "X-API-Key"


class EnvIn(BaseModel):
    base_url: str
    protected: bool = False
    auth: AuthIn = AuthIn()


class SecretIn(BaseModel):
    value: str | None = None


class ActiveIn(BaseModel):
    name: str


class App:
    """One open spec at a time plus the tabs listening for its events."""

    def __init__(self) -> None:
        self.events = Broadcaster()
        self.ws: Workspace | None = None

    async def open(self, path: Path) -> Workspace:
        await self.close()
        self.ws = Workspace(path, self.events.publish)
        store.remember({"path": str(path), "name": self.ws.name, "opened_at": time.time()})
        await self.ws.reload("open")
        self.ws.start()
        return self.ws

    async def close(self) -> None:
        if self.ws:
            await self.ws.stop()
            self.ws = None

    def need(self) -> Workspace:
        if not self.ws:
            raise HTTPException(409, "no spec open")
        return self.ws


def create_app(initial: Path | None = None) -> FastAPI:
    state = App()

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        if initial:
            await state.open(initial)
        yield
        await state.close()

    app = FastAPI(title="fumi", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.events = state.events
    api = [Depends(security.check)]

    @app.exception_handler(envs.EnvError)
    async def env_error(_request, e: envs.EnvError):
        return JSONResponse({"detail": str(e)}, status_code=e.status)

    async def changed() -> dict:
        ws = state.need()
        await state.events.publish({"type": "env", "workspace": ws.snapshot()})
        return ws.snapshot()

    @app.get("/api/session", dependencies=api)
    def session():
        return {"recent": store.recent(), "workspace": state.ws.snapshot() if state.ws else None}

    @app.delete("/api/recent", dependencies=api)
    def clear_recent():
        store.clear_recent()
        return {"recent": []}

    @app.post("/api/open", dependencies=api)
    async def open_spec(body: OpenIn):
        try:
            path = spec.resolve(body.path)
        except spec.SpecError as e:
            raise HTTPException(400, str(e))
        return (await state.open(path)).snapshot()

    @app.post("/api/close", dependencies=api)
    async def close_spec():
        await state.close()
        return {"ok": True}

    @app.post("/api/reload", dependencies=api)
    async def reload():
        ws = state.need()
        await ws.reload("reload")
        return ws.snapshot()

    @app.put("/api/env/active", dependencies=api)
    async def set_active(body: ActiveIn):
        envs.set_active(state.need().key, body.name)
        return await changed()

    @app.put("/api/envs/{name}", dependencies=api)
    async def put_env(name: str, body: EnvIn):
        envs.put(state.need().key, name, body.base_url, body.protected, body.auth.model_dump())
        return await changed()

    @app.delete("/api/envs/{name}", dependencies=api)
    async def delete_env(name: str):
        envs.delete(state.need().key, name)
        return await changed()

    @app.put("/api/envs/{name}/secrets/{secret}", dependencies=api)
    def put_secret(name: str, secret: str, body: SecretIn):
        ws = state.need()
        envs.get(ws.key, name)
        store.save_secret(ws.key, name, secret, (body.value or "").strip() or None)
        return ws.snapshot()

    @app.get("/api/branch-state", dependencies=api)
    def get_branch_state(branch: str):
        return store.branch_state(state.need().key, branch)

    @app.put("/api/branch-state", dependencies=api)
    async def put_branch_state(branch: str, request: Request):
        data = await request.json()
        if not isinstance(data, dict) or len(json.dumps(data)) > MAX_BRANCH_STATE:
            raise HTTPException(400, "branch state must be a JSON object under 2 MB")
        store.save_branch_state(state.need().key, branch, data)
        return {"ok": True}

    @app.post("/api/send", dependencies=api)
    async def send(body: SendIn):
        ws = state.need()
        env = envs.get(ws.key, body.env)
        method = body.method.upper()
        envs.check_write(env, method, body.confirm)
        url = env["base_url"] + "/" + body.path.lstrip("/")
        try:
            creds = await auth.for_request(ws.key, env, url, body.headers)
        except auth.AuthError as e:
            return {"error": str(e), "auth_error": True, "env": env["name"]}
        result = await sender.send(env["base_url"], method, body.path, body.query, [*body.headers, *creds.headers], body.body)
        return {**result, "env": env["name"], "auth": creds.applied}

    @app.get("/api/events", dependencies=api)
    async def events(request: Request):
        return StreamingResponse(state.events.stream(request.is_disconnected), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})

    app.mount("/", StaticFiles(directory=STATIC), name="static")
    return app
