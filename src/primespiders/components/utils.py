import asyncio
from typing import Any

from primespiders.utils import logger

# A set to keep track of low-level (spider level) background tasks.
BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()

def done_callback(task: asyncio.Task[Any]) -> None:
    if task.cancelled():
        logger.info(f"Task {task.get_name()} was cancelled.")
        return

    if (exc := task.exception()) is not None:
        logger.error(f"Task {task.get_name()} raised an exception: {exc}")
        return

    BACKGROUND_TASKS.discard(task)
    logger.info(f"Task {task.get_name()} completed successfully.")
