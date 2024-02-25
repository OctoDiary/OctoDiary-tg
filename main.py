#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from loguru import logger

from handlers import routers
from inline.manager import BotInlineManager
from utils.logs import init_loguru
from utils.texts import Texts

load_dotenv()


async def amain():
    token = os.getenv("TOKEN")
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dispatcher = Dispatcher(name="OctoDiary")
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
