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
from handlers.myschool.router import APIs, MySchool, MySchoolUser, isMySchoolUser, router
from octodiary.types.myschool.mobile.marks import Marks
from octodiary.types.myschool.mobile.marks import PayloadItem as MarkPayloadItem
from octodiary.types.myschool.mobile.short_subject_marks import PayloadItem as ShortSubjectPayloadItem
from octodiary.types.myschool.mobile.short_subject_marks import ShortSubjectMarks
from utils.other import handler, pluralization_string, sort_dict_by_date
from utils.other import mark as MARK
from utils.texts import Texts


def mark_info(mark: MarkPayloadItem):
    return Texts.MARK_INFO(
        SUBJECT_NAME=mark.subject_name,
        MARK=MARK(mark.value, mark.weight),
        CONTROL_FORM_NAME=mark.control_form_name,
        WEIGHT=pluralization_string(mark.weight, ["балл", "балла", "баллов"]),
        IS_EXAM_EMOJI="❗️" if mark.is_exam else "",
        UPDATED_AT=mark.updated_at.replace("T", " ")[:-3],
        COMMENT=mark.comment or "❌"
    )


def marks_sorted_by_date_info(marks: Marks):
    days = {}
    for mark in marks.payload:
        if (date_str := ".".join(mark.date[5:10].split("-")[::-1])) not in days:
            days[date_str] = {}

        if mark.subject_name not in days[date_str]:
            days[date_str][mark.subject_name] = []

        days[date_str][mark.subject_name] += [mark_info(mark)]

    return {
        date_str: Texts.MARKS_FOR_DATE(DATE=date_str) + "\n\n".join([
            "\n".join(marks)
            for subject, marks in subjects.items()
        ])
        for date_str, subjects in days.items()
    }


def dynamic(item):
    return "🔺" if item.dynamic == "UP" else "🔻" if item.dynamic == "DOWN" else ""


def marks_short_item(item: ShortSubjectPayloadItem, allow_goals: bool = False):
    marks = "<code>" + "</code>; <code>".join([MARK(mark.value, mark.weight) for mark in item.marks]) + "</code>" if item.marks else ""

    goals = (
        Texts.GOAL(
            ROUND=item.target.round,
            VALUE=item.target.value
        ) + Texts.OR.join([
            MARK(method.value, method.weight) + f"[{method.remain} шт.]"
            for method in item.target.paths
        ]) + "</code>\n"
    ) if allow_goals and item.target and item.target.round and item.target.paths else ""

    return Texts.SUBJECT_MARKS_INFO(
        SUBJECT_NAME=item.subject_name,
        AVERAGE=item.average,
        DYNAMIC=dynamic(item),
        GOALS=goals,
        PERIOD=item.period,
        START=item.start,
        END=item.end,
        COUNT=item.count,
        MARKS=marks or "❌"
    ) if item.average and item.count and item.period else ""


def marks_sorted_by_subject_info(marks_short: ShortSubjectMarks, goals: bool = False) -> dict[str, str]:
    return {
        (
            item
                .subject_name
                    .replace(Texts.OBZ, Texts.OBZ_SHORT)
                        .replace(Texts.PHIZ_KULTURA, Texts.PHIZ_KULTURA_SHORT)
        ): info
        for item in marks_short.payload
        if (info := marks_short_item(item=item, allow_goals=goals))
    }


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("marks_by_date")
)
@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == Texts.Buttons.MARKS_BY_DATE,
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def marks_by_date(message: Message, apis: APIs, user: User):
    """Marks users by date."""

    response = await message.answer(Texts.LOADING)

    marks = await apis.mobile.get_marks(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today() - timedelta(days=14),
        to_date=date.today(),
    )

    await message.bot.inline.list(
        update=response,
        row_width=5,
        **sort_dict_by_date(marks_sorted_by_date_info(marks), reverse=True)
    )


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("marks_by_subject")
)
@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == Texts.Buttons.MARKS_BY_SUBJECT,
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def marks_by_subject(message: Message, apis: APIs, user: User):
    """Marks users by subject."""

    response = await message.answer(Texts.LOADING)

    marks = await apis.mobile.get_subject_marks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id
    )

    await message.bot.inline.list(
        update=response,
        row_width=2,
        strings=marks_sorted_by_subject_info(
            marks,
            user.db_settings.get("goals", False)
        )
    )
