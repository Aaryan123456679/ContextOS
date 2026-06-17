"""Async utility helpers."""
import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("contextos")


async def safe_gather(*coros: Coroutine, engine_names: list[str] = None) -> list[Any]:
    """
    Run coroutines in parallel. If a coroutine raises, log the error and
    return None for that slot — the pipeline continues.
    """
    names = engine_names or [f"task_{i}" for i in range(len(coros))]

    async def _safe(coro, name):
        try:
            return await coro
        except Exception as e:
            logger.error("%s failed: %s", name, e)
            return None

    return list(await asyncio.gather(*[_safe(c, n) for c, n in zip(coros, names)]))


async def run_background(coro: Coroutine, label: str = "bg") -> None:
    """Fire-and-forget a coroutine, logging any exception."""
    try:
        await coro
    except Exception as e:
        logger.error("Background task '%s' failed: %s", label, e)


def create_background_task(coro: Coroutine, label: str = "bg") -> asyncio.Task:
    """Schedule a coroutine as a background asyncio task."""
    return asyncio.create_task(run_background(coro, label))
