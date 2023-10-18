#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date

from aiogram import F
from aiogram.filters import KICKED, ChatMemberUpdatedFilter, Command
from aiogram.types import Message

from database import Database
from handlers.admins.router import AdminRouter
from utils.texts import Texts

AdminFilter = F.func(lambda message: message.from_user.id in Database().admins)

db = Database()


@AdminRouter.message(Command("close"), AdminFilter)
async def close(message: Message):
    db.closed = True
    await message.answer(text=Texts.Admin.CLOSED_FOR_ALL_USERS)


@AdminRouter.message(Command("open"), AdminFilter)
async def open(message: Message):
    db.closed = False
    await message.answer(text=Texts.Admin.OPENED_FOR_ALL_USERS)


@AdminRouter.message(Command("statistics"), AdminFilter)
async def statistics(message: Message):
    await message.answer(text=Texts.Admin.STATISTICS(
        ALL_USERS_COUNT=len([
            user_id
            for user_id in db.keys()
            if user_id.isdigit() and db.user(user_id).system
        ]),
        NEW_USERS_IN_THIS_MONTH=db.settings.get(f"new-users-month:{date.today().month}", 0),
    ))


@AdminRouter.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def user_blocked_bot(message: Message):
    db.blocked_users = [*db.blocked_users, str(message.from_user.id)]
