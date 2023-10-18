#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import contextlib
from datetime import date

from aiogram import F
from aiogram.filters import KICKED, MEMBER, ChatMemberUpdatedFilter, Command
from aiogram.types import Message

from database import Database
from handlers.admins.router import AdminRouter
from utils.other import pluralization_string
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


@AdminRouter.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def user_unblocked_bot(message: Message):
    blocked_users = db.blocked_users
    blocked_users.remove(message.from_user.id)
    db.blocked_users = blocked_users


@AdminRouter.message(Command("notify"), AdminFilter)
async def notify(message: Message):
    if not message.reply_to_message:
        await message.answer(text=Texts.Admin.NOTIFY_NO_REPLY)
        return

    _message = await message.answer(
        text=Texts.Admin.NOTIFY_SENDING
    )

    notification_message = message.reply_to_message
    successfully_sent = 0
    for user in [
        int(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.user(user_id).system and int(user_id) not in db.blocked_users
    ]:
        await asyncio.sleep(3)
        with contextlib.suppress(Exception):
            await notification_message.copy_to(user)
            successfully_sent += 1

    await _message.edit_text(
        text=Texts.Admin.NOTIFY_SUCCESS.format(
            successfully_sent=pluralization_string(
                successfully_sent,
                ["польвателю", "пользователям", "пользователям"]
            )
        )
    )
