#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import contextlib
import os
from datetime import date

from aiogram import F
from aiogram.filters import KICKED, MEMBER, ChatMemberUpdatedFilter, Command, CommandObject
from aiogram.types import CallbackQuery, Message, ReactionTypeEmoji

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


@AdminRouter.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def user_blocked_bot(message: Message):
    if message.chat.id != message.from_user.id:
        return

    db.blocked_users = [*db.blocked_users, str(message.from_user.id)]


@AdminRouter.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def user_unblocked_bot(message: Message):
    if message.chat.id != message.from_user.id:
        return

    blocked_users = db.blocked_users
    blocked_users.remove(message.from_user.id)
    db.blocked_users = blocked_users


@AdminRouter.message(Command("notify"), AdminFilter)
async def notify(message: Message, command: CommandObject):
    if not message.reply_to_message:
        await message.answer(text=Texts.Admin.NOTIFY_NO_REPLY)
        return

    await message.bot.inline.answer(
        message,
        response=Texts.NOTIFY_CONFIRM,
        reply_markup=[
            {
                "text": Texts.Buttons.OK,
                "callback": start_notify,
                "kwargs": {
                    "message": message,
                    "command": command
                }
            },
            {
                "text": Texts.Buttons.CANCEL,
                "callback": delete
            }
        ]
    )


async def delete(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()


async def start_notify(callback: CallbackQuery, message, command: CommandObject):
    args = (command.args or "").split(" ")
    system = ""
    delete_users = False
    users_ids = []

    for arg in args:
        if arg in ["-s", "--system"]:
            system = args[args.index(arg) + 1]
        elif arg in ["-du", "--delete-users"]:
            delete_users = True
        elif arg in ["-u", "--users"]:
            users_ids_raw = args[args.index(arg) + 1]
            users_ids = [int(user_id) for user_id in users_ids_raw.split(",")]

    _message = await callback.message.edit_text(
        text=Texts.Admin.NOTIFY_SENDING
    )

    notification_message = message.reply_to_message
    successfully_sent = 0
    for user in [
        int(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.user(user_id).system and int(user_id) not in db.blocked_users
    ] if not users_ids else users_ids:
        if system and db.user(str(user)).system != system:
            continue

        await asyncio.sleep(3)
        with contextlib.suppress(Exception):
            await notification_message.copy_to(user)
            successfully_sent += 1

        if delete_users:
            db.set(str(user), {})

    await _message.edit_text(
        text=Texts.Admin.NOTIFY_SUCCESS.format(
            successfully_sent=pluralization_string(
                successfully_sent,
                ["пользователю", "пользователям", "пользователям"]
            )
        )
    )


@AdminRouter.message(Command("shutdown"), AdminFilter)
async def shutdown(message: Message):
    await message.react([ReactionTypeEmoji(emoji="👌")])
    os._exit(0)
