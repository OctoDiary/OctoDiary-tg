#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date, timedelta

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database import User
from handlers.myschool.router import APIs, MySchool, MySchoolUser, isMySchoolUser, router
from inline.types import AdditionalButtons
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
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("homeworks_upcoming")
)
@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == Texts.Buttons.HOMEWORKS_UPCOMING,
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def homeworks_upcoming(update: Message | CallbackQuery, apis: APIs, user: User):
    """Homeworks upcoming"""

    response = await update.bot.inline.answer(update, Texts.LOADING)

    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today(),
        to_date=(date.today() + timedelta(days=14))
    )

    await update.bot.inline.list(
        update=response,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": homeworks_upcoming,
                "kwargs": {
                    "apis": apis,
                    "user": user
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(homeworks_info(homeworks)),
    )


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("homeworks_past")
)
@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == Texts.Buttons.HOMEWORKS_PAST,
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def homeworks_past(update: Message | CallbackQuery, apis: APIs, user: User):
    """Homeworks past"""

    response = await update.bot.inline.answer(update, Texts.LOADING)

    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today() - timedelta(days=14),
        to_date=date.today() - timedelta(days=1)
    )

    await update.bot.inline.list(
        update=response,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": homeworks_past,
                "kwargs": {
                    "apis": apis,
                    "user": user
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(homeworks_info(homeworks), reverse=True)
    )
