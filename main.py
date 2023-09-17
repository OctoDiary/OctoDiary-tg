import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

# Load .env file, import inline manager and routers
from dotenv import load_dotenv
from handlers import routers
from inline.manager import BotInlineManager

load_dotenv()


async def main():
    bot = Bot(token=os.getenv("TOKEN"), parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    BotInlineManager(bot, dp, routers)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    if not os.getenv("TOKEN"):
        print("Please set TOKEN in .env file")
        exit()
        
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped! Exit...")
