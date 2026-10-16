"""Pushing events to every open browser tab over server-sent events."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Awaitable

KEEPALIVE_SECS = 15


class Broadcaster:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()

    async def publish(self, event: dict) -> None:
        for q in list(self._queues):
            q.put_nowait(event)

    def close(self) -> None:
        """End every open stream so shutdown doesn't wait on browser tabs."""
        for q in list(self._queues):
            q.put_nowait(None)

    async def stream(self, disconnected: Callable[[], Awaitable[bool]]) -> AsyncIterator[str]:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.add(q)
        try:
            yield "retry: 1500\n\n"
            while not await disconnected():
                try:
                    event = await asyncio.wait_for(q.get(), KEEPALIVE_SECS)
                    if event is None:
                        return
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            self._queues.discard(q)
