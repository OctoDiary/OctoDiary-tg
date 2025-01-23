#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio

from aiogram import Router

from core.misc.loop import loop
from core.services.database import database

router = Router(name="Loops")


@router.startup()
@loop(3)
async def redis_queue_poller():
    for func in database.redis._queue: # noqa
        try:
            await func
        except RuntimeError:
            pass

        database.redis._queue.remove(func) # noqa
