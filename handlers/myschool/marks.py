#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary


from datetime import date, timedelta
from aiohttp import ContentTypeError

from pydantic import ValidationError
from .router import router, MySchool, APIs, MySchoolUser
from aiogram.types import Message
from aiogram import F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import User
from octodiary.types.myschool.mobile.marks import Marks, PayloadItem as MarkPayloadItem
from octodiary.types.myschool.mobile.short_subject_marks import ShortSubjectMarks, PayloadItem as ShortSubjectPayloadItem
from utils.other import handler, sort_dict_dy_date, mark as MARK, pluralization_string


def mark_info(mark: MarkPayloadItem):
    return f"""┌ <b>Предмет</b>: <code>{mark.subject_name}</code>
├ <b>Оценка</b>: <code>{MARK(mark.value, mark.weight)}</code>
├ <b>Тип</b> работы: <code>{mark.control_form_name}</code> - {pluralization_string(mark.weight, ['балл', 'балла', 'баллов'])}{'❗️' if mark.is_exam else ''}
├ <b>Дата и время</b> выставления/изменения оценки: <code>{mark.updated_at.replace("T", " ")[:-3]}</code>
└ <b>Комментарий</b>: <code>{mark.comment or '❌'}</code>"""

def marks_sorted_by_date_info(marks: Marks):
    days = {}
    for mark in marks.payload:
        if (date_str := ".".join(mark.date[5:10].split("-")[::-1])) not in days:
            days[date_str] = {}
        
        if mark.subject_name not in days[date_str]:
            days[date_str][mark.subject_name] = []
        
        days[date_str][mark.subject_name] += [mark_info(mark)]
    
    return {
        date_str: f"📝 <b>Оценки за {date_str}:</b>\n\n" + "\n\n".join([
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
        f"├ <b>Цель</b>: <code>{item.target.round}</code> → <code>{item.target.value}</code>\n"
        + "├ <b>Нужные оценки для достижения цели</b>: <code>" + "</code> или <code>".join([
            MARK(method.value, method.weight) + f"[{method.remain} шт.]"
            for method in item.target.paths
        ]) + "</code>\n"
    ) if allow_goals and item.target and item.target.round and item.target.paths else ""
    return f"""┌ <b>Предмет</b>: <code>{item.subject_name}</code>
├ <b>Средний балл</b>: <code>{item.average}</code> {dynamic(item)}
{goals}├ <b>Период</b>: <code>{item.period}</code>
├ <b>Длительность периода</b>: {item.start} - {item.end}
├ <b>Количество оценок</b>: <code>{item.count}</code>
└ <b>Оценки</b>: {marks or '❌'}""" if item.average and item.count and item.period else ""


def marks_sorted_by_subject_info(marks_short: ShortSubjectMarks, goals: bool = False) -> dict[str, str]:
    return {
        (
            item
            .subject_name
            .replace("Основы безопасности жизнедеятельности", "ОБЖ")
            .replace("Физическая культура", "Физкультура")
        ): info
        for item in marks_short.payload
        if (info := marks_short_item(item=item, allow_goals=goals))
    }


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("marks_by_date")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Оценки [По дате]",
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def marks_by_date(message: Message, apis: APIs, user: User):
    """Оценки : По дате"""
    
    try:
        x = await apis.mobile.get(
            url="https://api.myschool.mosreg.ru/family/mobile/v1/marks",
            params={
                "student_id": user.db_profile["children"][0]["id"],
                "from": (date.today() - timedelta(days=14)).strftime("%Y-%m-%d"),
                "to": date.today().strftime("%Y-%m-%d"),
            },
            custom_headers={
                "x-mes-subsystem": "familymp",
                "client-type": "diary-mobile",
                "profile-id": user.db_profile_id,
            }, return_raw_response=True,
            model=Marks
        )
    except ContentTypeError:
        print(await x.text())
    

    try:
        marks = await apis.mobile.get_marks(
            student_id=user.db_profile["children"][0]["id"],
            profile_id=user.db_profile_id,
            from_date=date.today() - timedelta(days=14),
            to_date=date.today(),
        )
    except ValidationError as e:
        print(e.errors())


    await message.bot.inline.list(
        update=message,
        row_width=5,
        **sort_dict_dy_date(marks_sorted_by_date_info(marks))
    )


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("marks_by_subject")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Оценки [По предмету]",
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def marks_by_subject(message: Message, apis: APIs, user: User):
    """Оценки : По предмету"""

    marks = await apis.mobile.get_subject_marks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id
    )

    await message.bot.inline.list(
        update=message,
        row_width=2,
        strings=marks_sorted_by_subject_info(
            marks,
            user.db_settings.get("goals", False)
        )
    )
