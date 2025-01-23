#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import inspect
import logging
import typing
from contextlib import suppress
from types import FunctionType

from aiogram import Router

logger = logging.getLogger(__name__)


# Code fragments from https://github.com/hikariatama/Hikka/blob/master/hikka/loader.py
class StopLoopError(Exception):
    """Stops the loop, in which is raised"""


async def actual_loop(
        func,
        router: Router,
        *args,
        **kwargs
):
    router.__loop__[func.__name__]["status"] = True
    with suppress(KeyboardInterrupt):
        while router.__loop__[func.__name__].get("status", False):
            if router.__loop__[func.__name__].get("wait_before", False):
                await asyncio.sleep(router.__loop__[func.__name__]["interval"])

            func_params = list(inspect.signature(func).parameters.keys())
            try:
                await func(*args,  **{
                    attr: value
                    for attr, value in kwargs.items()
                    if attr in func_params
                })
            except StopLoopError:
                break
            except Exception:
                logger.exception(f"Loop error! <{func.__name__}> | <Router.{str(router.name)}")

            if not router.__loop__[func.__name__].get("wait_before", False):
                await asyncio.sleep(router.__loop__[func.__name__]["interval"])


def loop(
        interval: int = 20,
        wait_before: typing.Optional[bool] = False,
        router: typing.Optional[Router] = None
) -> FunctionType:
    """
    Create a new infinite loop for the specified <router>.startup function.

    :param interval: Loop iterations delay.
    :param wait_before: Insert delay before actual iteration, rather than after.
    :param router: The router to add the loop to.
    :return: The wrapped function.
    """

    def wrapped(func):
        """
        Wrapper function that adds loop functionality to the original function.

        :param func: The original function.
        :return: The new loop function.
        """

        async def new_loop_func(*args, **kwargs):
            """
            New loop function that either starts the loop for the router or calls the original function.

            :param args: Positional arguments for the original function.
            :param kwargs: Keyword arguments for the original function.
            :return: The result of the original function or None.
            """
            if _router := (router or kwargs.get("router")):
                logger.info(f"Loop {func.__name__} started for router {_router}")
                if getattr(_router, "__loop__", None) is None:
                    _router.__loop__ = {}

                _router.__loop__[func.__name__] = {
                    "wait_before": wait_before,
                    "interval": interval,
                    "task": asyncio.ensure_future(actual_loop(func=func, *args, **kwargs))
                }
            else:
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    logger.exception("Loop error! " + func.__name__)

        return new_loop_func

    return wrapped # noqa
