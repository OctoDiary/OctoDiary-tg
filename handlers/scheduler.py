#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import Message

import api
from apis import APIs
from database import User
from handlers.router import router
from handlers.schedule import ScheduleInfo
from utils.filters import apis_and_user
from utils.other import TIMEZONE, get_date, handler, sort_dict_by_date
from utils.texts import Texts


@router.message(Command("enable_scheduler"))
@handler()
@apis_and_user
async def enable_scheduler_cmd(message: Message, apis: APIs, user: User, bot: Bot):
    """Enable scheduler for current chat"""

    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            Texts.SCHEDULER_UNAVAILABLE_IN_PRIVATE_CHATS
        )
        return
    elif (
        await message.chat.get_member(message.from_user.id)
    ).status != ChatMemberStatus.CREATOR:
        await message.answer(
            Texts.YOU_MUST_BE_OWNER
        )
        return
    elif str(message.chat.id) in user.get("scheduler", {}):
        await message.answer(
            Texts.SCHEDULER_ALREADY_ENABLED
        )
        return

    user.db_scheduler = user.get("scheduler", {}) | {
        str(message.chat.id): {
            "chat_id": message.chat.id,
            "message_thread_id": message.message_thread_id,
            "is_topic": message.is_topic_message,
            "message_reply_id": getattr(message.reply_to_message, "message_id", None)
        }
    }

    await message.answer(
        Texts.SCHEDULER_ENABLED
    )

    await run_scheduler_for_chat(
        chat_id=str(message.chat.id),
        apis=apis,
        user=user,
        bot=bot,
        first_start=True
    )


@router.message(Command("disable_scheduler"))
@handler()
@apis_and_user
async def disable_scheduler_cmd(message: Message, user: User, apis):
    """Disable scheduler for current chat"""

    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            Texts.SCHEDULER_UNAVAILABLE_IN_PRIVATE_CHATS
        )
        return
    elif (
        await message.chat.get_member(message.from_user.id)
    ).status != ChatMemberStatus.CREATOR:
        await message.answer(
            Texts.YOU_MUST_BE_OWNER
        )
        return
    elif str(message.chat.id) not in user.get("scheduler", {}):
        await message.answer(
            Texts.SCHEDULER_NOT_ENABLED
        )
        return

    user.pop_key("scheduler", str(message.chat.id))

    await message.answer(
        Texts.SCHEDULER_DISABLED
    )


async def run_scheduler_for_chat(
        chat_id: str,
        apis: APIs,
        user: User,
        bot: Bot,
        *,
        first_start: bool = False
):
    scheduler = user.db_scheduler
    scheduler_info = scheduler[chat_id]

    def get_message_with_bot(_message: Message):
        _message.as_(bot=bot)
        return _message

    today = get_date()
    weekday = today.weekday()
    weeks = [
        await api.get_events(
            begin_date=today - timedelta(days=x),
            end_date=today + timedelta(days=y),
            user=user,
            apis=apis
        )
        for x, y in [
            (
                -(0 - weekday),
                6 - weekday
            ),
            (
                -(7 - weekday),
                13 - weekday
            ),
            (
                -(14 - weekday),
                20 - weekday
            )
        ]
    ]

    for index, week_events_data in enumerate(weeks):
        week_events = week_events_data.response
        if week_events.total_count == 0:
            continue

        message: Message = await bot.inline.list(
            update=(
                get_message_with_bot(
                    Message(
                        chat=(await bot.get_chat(chat_id=int(chat_id))),
                        from_user=(
                            await bot.get_me()
                        ),
                        date=datetime.now(tz=TIMEZONE),
                        **scheduler_info.get("weeks_messages", {})[str(index)]
                    )
                )
                if str(index) in scheduler_info.get("weeks_messages", {}) and not first_start
                else (
                    await bot.get_chat(chat_id=int(chat_id))
                )
            ),
            row_width=5,
            disable_deadline=True,
            **(
                sort_dict_by_date(
                    dictionary=ScheduleInfo(
                        events=week_events_data,
                        user=user,
                        inline=True,
                        exclude_marks=True
                    ).inline_strings()
                ) | (
                    (
                        {
                            "message_thread_id": scheduler_info["message_thread_id"],
                        }
                        if scheduler_info["is_topic"]
                        else {
                            "reply_to_message_id": scheduler_info["message_reply_id"],
                        }
                    ) if str(index) not in scheduler_info.get("weeks_messages", {}) or first_start else {}
                )
            )
        )

        if "weeks_messages" not in scheduler_info:
            scheduler_info["weeks_messages"] = {}

        if message:
            scheduler_info["weeks_messages"][str(index)] = {
                "message_id": message.message_id,
                "message_thread_id": message.message_thread_id,
                "is_topic_message": message.is_topic_message,
            }

    user.db_scheduler = scheduler
