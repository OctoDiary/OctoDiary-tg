#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import timedelta

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from apis import APIs
from database import Database, User
from handlers.router import router
from octodiary.exceptions import APIError
from octodiary.types.mobile import Visits
from utils.filters import apis_and_user
from utils.other import get_date, handler
from utils.texts import Texts


def visits_info(visits: Visits) -> str:
    visits.payload.reverse()

    return "\n\n".join(
        [
            Texts.Mes.VISIT(VISIT=visit, DATE=day.date)
            for day in visits.payload
            for visit in day.visits
            if visit.type == "COMMON"
        ]
    )


@router.message(
    F.func(lambda message: Database().user(message.from_user.id).system == "mes"),
    Command("visits")
)
@router.message(
    F.func(lambda message: Database().user(message.from_user.id).system == "mes"),
    F.text == Texts.Buttons.VISITS,
    F.chat.type == ChatType.PRIVATE
)
@handler()
@apis_and_user
async def visits_cmd(update: Message | CallbackQuery, apis: APIs, user: User, *, is_inline: bool = False):
    """Visits information"""
    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    try:
        today = get_date()
        visits = await apis.mobile.get_visits(
            profile_id=user.db_profile_id,
            student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
            contract_id=user.db_current_child["contract_id"] if user.db_current_child else user.db_profile["children"][0]["contract_id"],
            from_date=today - timedelta(days=14),
            to_date=today,
        )
    except APIError as e:
        await update.bot.inline.answer(
            response,
            response=Texts.API_ERROR(ERROR=e)
        )
        return
    
    await update.bot.inline.answer(
        response,
        response=visits_info(visits),
        reply_markup={
            "text": Texts.Buttons.UPDATE,
            "callback": visits_cmd,
            "kwargs": {
                "user": user,
                "apis": apis,
                "is_inline": is_inline
            },
            "reusable": True,
            "disable_deadline": True
        },
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)
