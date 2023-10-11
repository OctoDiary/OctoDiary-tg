#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import logging
import os
import sys
from logging import getLogger

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

# Load .env file, import inline manager and routers
from dotenv import load_dotenv

from handlers import routers
from inline.manager import BotInlineManager
from utils.texts import Texts

load_dotenv()

logger = getLogger(__name__)

async def amain():
    token = os.getenv("TOKEN")
    bot = Bot(token=token, parse_mode=ParseMode.HTML)

    dispatcher = Dispatcher(name="OctoDiary")
    BotInlineManager(bot, dispatcher, routers)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


def main():
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(amain())
    except KeyboardInterrupt:
        logger.info("Bot stopped! Exit...")


if __name__ == "__main__":
    if not os.getenv("TOKEN"):
        logger.warning(Texts.SET_TOKEN_IN_ENV)
        sys.exit()

    main()
