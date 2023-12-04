#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date, timedelta

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database import User
from handlers.mes.router import APIs, Mes, MesUser, isMesUser, router
from octodiary.exceptions import APIError
from octodiary.types.mes.mobile import Visits
from utils.other import handler
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
    F.func(isMesUser),
    Command("visits"),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
)
@router.message(
    F.func(isMesUser),
    F.text == "Посещение",
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def visits_cmd(update: Message | CallbackQuery, apis: APIs, user: User):
    """Visits information"""
    response = await update.bot.inline.answer(update, Texts.LOADING)

    try:
        today = date.today()
        visits = await apis.mobile.get_visits(
            profile_id=user.db_profile_id,
            student_id=user.db_profile["children"][0]["id"],
            contract_id=user.db_profile["children"][0]["contract_id"],
            from_date=today - timedelta(days=14),
            to_date=today,
        )
    except APIError as e:
        await update.bot.inline.answer(
            response,
            response=Texts.API_ERROR(ERROR=e)
        )
        return
    
    return await update.bot.inline.answer(
        response,
        response=visits_info(visits),
        reply_markup={
            "text": Texts.Buttons.UPDATE,
            "callback": visits_cmd,
            "kwargs": {
                "user": user,
                "apis": apis,
            },
            "reusable": True,
            "disable_deadline": True
        },
    )
