import asyncio
import logging
import typing
from types import FunctionType

from aiogram import Router

logger = logging.getLogger(__name__)


class StopLoop(Exception):
    """Stops the loop, in which is raised"""


async def actual_loop(
    func,
    router: Router,
    *args, **kwargs
):
    info = router.__loop__
    info["status"] = True
    try:
        while info.get("status", False):
            if info.get("wait_before", False):
                await asyncio.sleep(router.interval)
            
            try:
                await func(router=router, *args, **kwargs)
            except StopLoop:
                break
            except Exception:
                logger.exception("Loop error! " + func.__name__ + " | " + str(router))
            
            if not info.get("wait_before", False):
                await asyncio.sleep(info["interval"])
    except: pass


def loop(
    interval: int = 20,
    wait_before: typing.Optional[bool] = False,
) -> FunctionType:
    """
    Create new infinite loop from class method
    :param interval: Loop iterations delay
    :param wait_before: Insert delay before actual iteration, rather than after
    """

    def wrapped(func):
        async def new_loop_func(*args, **kwargs):
            router = kwargs.get("router")
            logger.info("Started loop for %s", func)
            router.__loop__ = {
                "wait_before": wait_before,
                "interval": interval,
            }
            if not router.__loop__.get("task", None):
                router.__loop__["task"] = asyncio.ensure_future(actual_loop(func=func, *args, **kwargs))

        return new_loop_func

    return wrapped
