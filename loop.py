#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import logging
import typing
from contextlib import suppress
from types import FunctionType

from aiogram import Router

logger = logging.getLogger(__name__)


class StopLoop(Exception):
    """Stops the loop, in which is raised"""


async def actual_loop(
    func, router: Router,
    *args, **kwargs
):
    router.__loop__["status"] = True
    with suppress(KeyboardInterrupt):
        while router.__loop__.get("status", False):
            if router.__loop__.get("wait_before", False):
                await asyncio.sleep(router.interval)
            
            try:
                await func(router=router, *args, **kwargs)
            except StopLoop:
                break
            except Exception:
                logger.exception("Loop error! " + func.__name__ + " | " + str(router))
            
            if not router.__loop__.get("wait_before", False):
                await asyncio.sleep(router.__loop__["interval"])


def loop(
    interval: int = 20,
    wait_before: typing.Optional[bool] = False,
) -> FunctionType:
    """
    Create new infinite loop for specified <router>.startup function
    :param interval: Loop iterations delay
    :param wait_before: Insert delay before actual iteration, rather than after
    """

    def wrapped(func):
        async def new_loop_func(*args, **kwargs):
            if router := kwargs.get("router"):
                logger.info(f"Loop {func.__name__} started for router {router}")
                router.__loop__ = {
                    "wait_before": wait_before,
                    "interval": interval,
                    "task": asyncio.ensure_future(actual_loop(func=func, *args, **kwargs))
                }
            else:
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    logger.exception("Loop error! " + func.__name__ + " | " + str(router))
            

        return new_loop_func

    return wrapped
