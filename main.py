#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import os
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from core.dispatcher import dispatcher
from loguru import logger
load_dotenv()

from core.routers import routers # noqa
from core.misc.texts import Texts # noqa
from core.misc.inline.manager import BotInlineManager # noqa
from core.services.logs import init_loguru # noqa


async def amain():
    token = os.getenv("TOKEN")
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    BotInlineManager(bot, dispatcher, routers)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


def main():
    try:
        logger.info("Bot started!")
        asyncio.run(amain())
    except KeyboardInterrupt:
        logger.info("Bot stopped! Exit...")


if __name__ == "__main__":
    init_loguru()
    if not os.getenv("TOKEN"):
        logger.warning(Texts.SET_TOKEN_IN_ENV)
        sys.exit()

    main()
