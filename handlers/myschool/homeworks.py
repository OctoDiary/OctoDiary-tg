#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date, timedelta

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from database import User
from octodiary.types.myschool.mobile import ShortHomeworks
from utils import keyboard
from utils.other import handler, sort_dict_dy_date

from .router import APIs, MySchool, MySchoolUser, router


def homeworks_info(homeworks: ShortHomeworks):
    days = {}
    for homework in homeworks.payload:
        if (date_str := homework.date.strftime("%d.%m")) not in days:
            days[date_str] = {}
        
        if homework.subject_name not in days[date_str]:
            days[date_str][homework.subject_name] = []
        
        days[date_str][homework.subject_name] += [f"<code>{homework.description}</code>"]
    
    return {
        date_str: f"📝 <b>Домашние задания на {date_str}:</b>\n\n" + "\n".join([
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
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("homeworks_upcoming")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Д/З [Ближайшее]",
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def homeworks_upcoming(message: Message, apis: APIs, user: User):
    """Домашние задания (ДЗ) : Ближайшее"""

    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today(),
        to_date=(date.today() + timedelta(days=7))
    )
    
    await message.bot.inline.list(
        update=message,
        row_width=5,
        **sort_dict_dy_date(homeworks_info(homeworks)),
    )


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("homeworks_past")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Д/З [Прошедшее]",
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def homeworks_past(message: Message, apis: APIs, user: User):
    """Домашние задания (ДЗ) : Прошедшее"""

    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today() - timedelta(days=7),
        to_date=date.today() - timedelta(days=1)
    )
    
    await message.bot.inline.list(
        update=message,
        row_width=5,
        **sort_dict_dy_date(homeworks_info(homeworks), reverse=True)
    )

