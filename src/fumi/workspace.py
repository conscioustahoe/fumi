"""The open spec file: the API it describes and a watcher that reloads it on edits and branch switches."""

import asyncio
import contextlib
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from watchfiles import awatch

from fumi import envs, gitinfo, openapi, spec, store

Publish = Callable[[dict], Awaitable[None]]
NO_BRANCH = "-"  # state key for a spec that isn't in a git repo


class Workspace:
    def __init__(self, spec_path: Path, publish: Publish):
        self.spec = spec_path
        self.key = store.workspace_key(spec_path)
        self.repo = gitinfo.toplevel(spec_path.parent)
        self.name = (self.repo or spec_path.parent).name
        self.git = gitinfo.state(self.repo) if self.repo else None
        self.ops: list[dict] = []
        self.error: str | None = None
        self.good: dict | None = None  # where the shown ops were read. Kept when a later read fails
        self.loaded_at: float | None = None
        self._publish = publish
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    @property
    def branch(self) -> str:
        return self.git.branch if self.git else NO_BRANCH

    def snapshot(self) -> dict:
        env = envs.get(self.key)
        return {
            "name": self.name,
            "spec": str(self.spec),
            "spec_rel": str(self.spec.relative_to(self.repo)) if self.repo else self.spec.name,
            "git": self.git is not None,
            "branch": self.branch,
            "sha": self.git.sha if self.git else None,
            "error": self.error,
            "good": self.good,
            "loaded_at": self.loaded_at,
            "env": env["name"],
            "base_url": env["base_url"],
            "envs": envs.public(self.key),
            "ops": self.ops,
        }

    async def reload(self, reason: str) -> None:
        """Read the spec again. On failure the last good operations stay and the error says why."""
        async with self._lock:
            previous = self.ops if self.good else None
            if self.repo:
                self.git = gitinfo.state(self.repo)
            try:
                self.ops = openapi.flatten(spec.read(self.spec))
                self.error = None
                self.good = {"branch": self.branch, "sha": self.git.sha if self.git else None}
            except spec.SpecError as e:
                self.error = str(e)
            self.loaded_at = time.time()
            diff = None if self.error else openapi.diff(previous, self.ops)
        await self._publish({"type": "spec", "reason": reason, "diff": diff, "workspace": self.snapshot()})

    # ---- watching ----

    def start(self) -> None:
        self._task = asyncio.create_task(self._watch())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task

    async def _watch(self) -> None:
        # Not recursive: the spec's own folder catches edits and HEAD catches every checkout.
        folder = self.spec.parent
        gdir = gitinfo.git_dir(self.repo) if self.repo else None
        target = os.path.realpath(self.spec)
        heads = {os.path.realpath(gdir / n) for n in ("HEAD", "packed-refs")} if gdir else set()

        def relevant(_change, path: str) -> bool:
            real = os.path.realpath(path)
            return real == target or real in heads

        paths = [folder, *([gdir] if gdir else [])]
        async for _ in awatch(*paths, watch_filter=relevant, debounce=300, recursive=False, stop_event=self._stop):
            await self.reload("change")
