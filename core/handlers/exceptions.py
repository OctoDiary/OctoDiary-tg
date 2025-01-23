#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import os
import uuid
from typing import Callable, Dict, Any, Awaitable

from aiogram import Bot, enums
from aiogram.types import ErrorEvent, BufferedInputFile, Message
from loguru import logger

from core.dispatcher import dispatcher
from core.misc.texts import Texts
from core.misc.utils import escape_html
from core.services.database import database


@dispatcher.error()
async def error_handler(event: ErrorEvent, bot: Bot):
    update = (
        event.update.message
        if event.update.message
        else event.update.callback_query
        if event.update.callback_query
        else event.update.inline_query
        if event.update.inline_query
        else None
    )
    if not update:
        return

    user = update.from_user

    system = database.user(str(user.id)).system or "Unknown"
    uid = str(uuid.uuid4().hex)
    logger.bind(
        user_id=user.id,
        username=user.username,
        system=system,
        uid=uid
    ).exception(event.exception)
    with open("logs/user_errors.log", mode="rb") as f:
        file = f.read()
    with open("logs/user_errors.log", mode="w") as f:
        f.write("")

    await bot.send_message(update.from_user.id, Texts.INTERNAL_ERROR(UUID=uid))
    await bot.send_document(
        os.environ.get("ADMINS_CHAT_ID"),
        BufferedInputFile(
            file,
            filename=f"{uid}.log",
        ),
        # .from_file(
        #     f"logs/user_errors.log",
        #     filename=f"{uid}.log"
        # ),
        message_thread_id=16681,
        caption=Texts.ERROR_INFO(
            UUID=uid, system=system,
            user_id=user.id,
            username=user.username,
            update_type=update.__class__.__name__,
            error_name=event.exception.__class__.__name__,
            error_message=escape_html(str(event.exception))
        ),
        disable_notification=True,
    )


@dispatcher.message.outer_middleware()
async def message_middleware(
    handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
    message: Message,
    data: Dict[str, Any]
):
    """Save user id in database"""
    if (
        message.chat.type == enums.ChatType.PRIVATE
        and message.from_user.id not in database.settings.get("full-users-ids", [])
    ):
        database.settings.set(
            "full-users-ids",
            [*database.settings.get("full-users-ids", []), message.from_user.id]
        )

    return await handler(message, data)
