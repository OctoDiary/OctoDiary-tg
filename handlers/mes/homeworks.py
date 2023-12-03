#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date, timedelta

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from database import User
from handlers.mes.router import APIs, Mes, MesUser, isMesUser, router
from octodiary.types.myschool.mobile import ShortHomeworks
from utils.other import handler, sort_dict_by_date
from utils.texts import Texts


def homeworks_info(homeworks: ShortHomeworks):
    days = {}
    for homework in homeworks.payload:
        if (date_str := homework.date.strftime("%d.%m")) not in days:
            days[date_str] = {}

        if homework.subject_name not in days[date_str]:
            days[date_str][homework.subject_name] = []

        days[date_str][homework.subject_name] += [f"<code>{homework.description}</code>"]

    return {
        date_str: Texts.HOMEWORKS_FOR_DATE(DATE=date_str) + "\n".join([
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


@router.message(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    Command("homeworks_upcoming")
)
@router.message(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.text == Texts.Buttons.HOMEWORKS_UPCOMING,
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def homeworks_upcoming(message: Message, apis: APIs, user: User):
    """Homeworks upcoming"""

    response = await message.answer(Texts.LOADING)

    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today(),
        to_date=(date.today() + timedelta(days=14))
    )

    await message.bot.inline.list(
        update=response,
        row_width=5,
        **sort_dict_by_date(homeworks_info(homeworks)),
    )


@router.message(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    Command("homeworks_past")
)
@router.message(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.text == Texts.Buttons.HOMEWORKS_PAST,
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def homeworks_past(message: Message, apis: APIs, user: User):
    """Homeworks past"""

    response = await message.answer(Texts.LOADING)

    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today() - timedelta(days=14),
        to_date=date.today() - timedelta(days=1)
    )

    await message.bot.inline.list(
        update=response,
        row_width=5,
        **sort_dict_by_date(homeworks_info(homeworks), reverse=True)
    )
