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


class StopLoopError(Exception):
    """Stops the loop, in which is raised"""


class Loop:
    def __init__(
        self,
        interval: int = 20,
        *,
        wait_before: typing.Optional[bool] = False
    ):
        self.interval = interval
        self.wait_before = wait_before
        self.task = None
        self.running = False

    async def __call__(self, *args, **kwargs):
        pass

    def _stop(self, *args, **kwargs):
        self._wait_for_stop.set()

    def stop(self, *args, **kwargs):
        if self._task:
            logger.debug("Stopped loop for method %s", self.func)
            self._wait_for_stop = asyncio.Event()
            self.status = False
            self._task.add_done_callback(self._stop)
            self._task.cancel()
            return asyncio.ensure_future(self._wait_for_stop.wait())

        logger.debug("Loop is not running")
        return asyncio.ensure_future(stop_placeholder())

    def start(self, *args, **kwargs):
        if not self._task:
            logger.debug("Started loop for method %s", self.func)
            self._task = asyncio.ensure_future(self.actual_loop(*args, **kwargs))
        else:
            logger.debug("Attempted to start already running loop")

    async def actual_loop(self, *args, **kwargs):
        # Wait for loader to set attribute
        while not self.module_instance:
            await asyncio.sleep(0.01)

        if isinstance(self._stop_clause, str) and self._stop_clause:
            self.module_instance.set(self._stop_clause, True)

        self.status = True

        while self.status:
            if self._wait_before:
                await asyncio.sleep(self.interval)

            if (
                    isinstance(self._stop_clause, str)
                    and self._stop_clause
                    and not self.module_instance.get(self._stop_clause, False)
            ):
                break

            try:
                await self.func(self.module_instance, *args, **kwargs)
            except StopLoop:
                break
            except Exception:
                logger.exception("Error running loop!")

            if not self._wait_before:
                await asyncio.sleep(self.interval)

        self._wait_for_stop.set()

        self.status = False

    def __del__(self):
        self.stop()

async def actual_loop(
    func,
    router: Router,
    **kwargs
):
    router.__loop__["status"] = True
    with suppress(KeyboardInterrupt):
        while router.__loop__.get("status", False):
            if router.__loop__.get("wait_before", False):
                await asyncio.sleep(router.interval)

            try:
                await func(router=router, **kwargs)
            except StopLoopError:
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
    Create a new infinite loop for the specified <router>.startup function.

    :param interval: Loop iterations delay.
    :param wait_before: Insert delay before actual iteration, rather than after.
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
