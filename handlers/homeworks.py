#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import api
from apis import APIs
from database import User
from handlers.router import router
from inline.types import AdditionalButtons
from octodiary.types.mobile import ShortHomeworks
from utils.filters import apis_and_user
from utils.other import handler, sort_dict_by_date
from utils.texts import Texts


def homeworks_info(response: api.APIResponse[ShortHomeworks]):
    days = {}
    for homework in response.response.payload:
        if (date_str := homework.date.strftime("%d.%m")) not in days:
            days[date_str] = {}

        if homework.subject_name not in days[date_str]:
            days[date_str][homework.subject_name] = []

        days[date_str][homework.subject_name] += [f"<code>{homework.description}</code>"]

    return {
        date_str: (
            Texts.FROM_CACHE(response.last_cache_time) if response.is_cache else ""
        ) + Texts.HOMEWORKS_FOR_DATE(DATE=date_str) + "\n".join([
            f"• <b>{subject}</b>"
            + (
                ("\n   ├ " if len(homeworks) > 1 else "")
                + "\n   ├ ".join(homeworks[:-1])
                + f"\n   └ {homeworks[-1]}"
            )
            for subject, homeworks in subjects.items()
        ])
        for date_str, subjects in days.items()
    }


@router.message(Command("homeworks_upcoming"))
@router.message(F.text == Texts.Buttons.HOMEWORKS_UPCOMING, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def homeworks_upcoming(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        *,
        is_inline: bool = False
):
    """Homeworks upcoming"""

    response = update if is_inline else await update.bot.inline.answer(update, Texts.LOADING)

    response_data = await api.get_homeworks(user=user, apis=apis, type=api.HomeworkTypes.UPCOMING)

    await update.bot.inline.list(
        update=response,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": homeworks_upcoming,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": is_inline
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(homeworks_info(response_data)),
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)


@router.message(Command("homeworks_past"))
@router.message(F.text == Texts.Buttons.HOMEWORKS_PAST, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def homeworks_past(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        *,
        is_inline: bool = False
):
    """Past homeworks info"""

    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    response_data = await api.get_homeworks(user=user, apis=apis, type=api.HomeworkTypes.PAST)

    await update.bot.inline.list(
        update=response,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": homeworks_past,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": is_inline
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(homeworks_info(response_data), reverse=True)
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)
