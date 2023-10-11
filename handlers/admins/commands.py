#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message

from database import Database
from handlers.admins.router import AdminRouter
from utils.texts import Texts

AdminFilter = F.func(lambda message: message.from_user.id in Database().admins)

@AdminRouter.message(Command("close"), AdminFilter)
async def close(message: Message):
    Database().closed = True
    await message.answer(text=Texts.Admin.CLOSED_FOR_ALL_USERS)


@AdminRouter.message(Command("open"), AdminFilter)
async def open(message: Message):
    Database().closed = False
    await message.answer(text=Texts.Admin.OPENED_FOR_ALL_USERS)


@AdminRouter.message(Command("statistics"), AdminFilter)
async def statistics(message: Message):
    db = Database()
    await message.answer(text=Texts.Admin.STATISTICS(
        ALL_USERS_COUNT=len(db.settings.get("users", [])),
        NEW_USERS_IN_THIS_MONTH=Database().settings.get(f"new-users-month:{date.today().month}", 0),
    ))
