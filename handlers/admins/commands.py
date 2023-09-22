#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatType
from database import Database
from .router import AdminRouter


@AdminRouter.message(Command("close"), F.func(lambda message: message.from_user.id in Database().admins))
async def close(message: Message):
    Database().closed = True
    await message.answer("Бот <b>закрыт</b> для <b>всех</b> пользователей.")


@AdminRouter.message(Command("open"), F.func(lambda message: message.from_user.id in Database().admins))
async def open(message: Message):
    Database().closed = False
    await message.answer("Бот <b>открыт</b> для <b>всех</b> пользователей.")
