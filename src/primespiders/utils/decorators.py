from collections.abc import Coroutine

from primespiders.utils import ENV, logger


def prevent_side_effects(func: Coroutine):
    """Decorator to skip the execution of a coroutine 
    if the DEBUG mode is enabled. This is useful for
    functions that download files or perform other 
    side effects.
    
    Args:
        func (Coroutine): The coroutine function to be decorated.
    """
    async def wrapper(*args, **kwargs):
        debug_mode = ENV.boolean('DEBUG')
        if not debug_mode:
            return await func(*args, **kwargs)
        logger.info(f"Skipping execution of {func.__name__} due to DEBUG mode.")
    return wrapper
