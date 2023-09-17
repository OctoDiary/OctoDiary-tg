from datetime import date, datetime, timedelta
from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, ChosenInlineResult, InlineQuery, Message
from database import User
from octodiary.exceptions import APIError
from octodiary.types.myschool.mobile import EventsResponse
from octodiary.types.myschool.mobile.lesson_schedule_items import (
    LessonHomework,
    LessonScheduleItems,
    Mark,
)
from utils.other import pluralization_string

from .router import APIs, MySchool, MySchoolUser, router


def day_schedule_info(evets: EventsResponse, from_db):
    days_lessons = {}
    def weekday(x):
        return {0: "понедельник", 1: "вторник", 2: "среду", 3: "четверг", 4: "пятницу", 5: "субботу", 6: "воскресенье"}[int(x)]
    
    for event in evets.response:
        if event.lesson_type != "NORMAL":
            continue
        
        start = datetime.strptime(event.start_at, "%Y-%m-%dT%H:%M:%S%z")
        end = datetime.strptime(event.finish_at, "%Y-%m-%dT%H:%M:%S%z")
        
        date = start.date()
        date_str = f"{date.day:02}.{date.month:02}/{date.weekday()}"

        if date_str not in days_lessons:
            days_lessons[date_str] = []

        homeworks = [
            homework.replace("\n", "</code>; <code>")
            for homework in event.homework.descriptions
        ] if event.homework and event.homework.descriptions else []

        days_lessons[date_str].append(
            (
                f"• <b>{event.subject_name}</b>  "
                f"[<code>{start.hour:02}:{start.minute:02}-{end.hour:02}:{end.minute:02}</code>]    "
                f"[<b>ID</b>: <code>{event.id}</code>]"
            )
            + (f"\n  {'├' if event.cancelled or homeworks or event.marks else '└'} <b>Замена</b>: ✅" if event.replaced else '')
            + (f"\n  {'├' if homeworks or event.marks else '└'} <b>Отмена</b>: ✅" if event.cancelled else '')
            + (
                (
                    f"\n  {'├' if homeworks else '└'} <b>Оценки</b>: " + " | ".join([f"<code>{mark.value}</code> [<code>{mark.weight}</code>]" for mark in event.marks])
                ) if event.marks else ""
            )
            + (
                (
                    (
                        (
                            "\n  ├ <b>ДЗ</b>: <code>"
                            + "</code>\n  ├ <b>ДЗ</b>: <code>".join(homeworks[:-1])
                            + "</code>"
                        ) if len(homeworks) > 1 else ""
                    )
                    + f"\n  └ <b>ДЗ</b>: <code>{homeworks[-1]}</code>"
                ) if homeworks else ""
            )
        )
    
    return {
        date_str.split("/")[0]: f"""
🗓 <b>Расписание на {weekday(date_str.split("/")[1])}</b> [<code>{date_str.split("/")[0]}</code>]
{from_db}
""" + "\n".join(lessons) + """

<b>Подробная информация</b> об уроке: <code>/lesson ID</code>
"""
        for date_str, lessons in days_lessons.items()
    }

def mark_info(mark: Mark) -> str:
    return f"""┌ <b>Оценка</b>: <code>{mark.value}</code>
├ <b>Тип работы</b>: <code>{mark.control_form_name}</code>
├ <b>Вес:</b> <code>{pluralization_string(mark.weight, ['балл', 'балла', 'баллов'])}</code>
├ <b>Время выставления</b>: <code>{mark.updated_at.strftime("%d.%m.%Y %H:%M")}</code>
└ <b>Комментарий</b>: <code>{mark.comment or "❌"}</code>"""

def homework_info(homework: LessonHomework) -> str:
    files = [
        f"<a href='{file.link}'>{file.title}</a>"
        for material in homework.materials
        for file in material.items
    ] if homework.materials else []

    return f"""┌ <b>Задание</b>: <code>{homework.homework}</code>
└ <b>Прикреплённые файлы: {'✅' if files else '❌'}</b>""" + (
        (
            ("\n   ├ " if len(files) > 1 else "")
            + "\n   ├ ".join(files[:-1])
            + f"\n   └ {files[-1]}"
        ) if files else ""
    )


def lesson_info(lesson: LessonScheduleItems) -> str:
    return f"""
<b>Подробная информация</b> об уроке: <code>{lesson.id}</code>

• <b>Предмет</b>: <code>{lesson.subject_name}</code>
• <b>Преподаватель</b>: <code>{lesson.teacher.last_name} {lesson.teacher.first_name} {lesson.teacher.middle_name}</code>
• <b>Время</b>: <code>{lesson.begin_time} - {lesson.end_time}</code>
• <b>Дата</b>: <code>{lesson.date}</code>
• <b>Кабинет</b>: <code>{lesson.room_number}</code>""" + (
        (
            "\n\n[ <b>Оценки</b> ]\n"
            + (
                "\n".join([mark_info(mark) for mark in lesson.marks])
            )
        ) if lesson.marks else ""
    ) + (
        (
            "\n\n[ <b>Домашнее задание</b> ]\n"
            + (
                "\n".join([homework_info(homework) for homework in lesson.lesson_homeworks])
            )
        ) if lesson.lesson_homeworks else ""
    )


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("schedule")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Расписание",
    F.chat.type == ChatType.PRIVATE
)
async def schedule(message: Message, apis: APIs, user: User):
    """Расписание"""

    from_db = ""
    try:
        today = date.today()
        events = await apis.mobile.get_events(
            person_id=user.db_profile["children"][0]["contingent_guid"],
            mes_role=user.db_profile["profile"]["type"],
            begin_date=(
                today - timedelta(days= -1*(0 - today.weekday()))
            ),
            end_date=(
                today + timedelta(days= 7+(6 - today.weekday()))
            )
        )
    except APIError:
        events = user.db_events
        from_db = "<tg-spoiler>❕ Сервер не ответил на запрос, последние загруженные данные:</tg-spoiler>\n"

    strings = day_schedule_info(events, from_db)
    await message.bot.inline.list(
        message, strings, row_width=5,
    )


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("lesson")
)
async def get_lesson_info(message: Message, apis: APIs, user: User, command: CommandObject):
    """Получить информацию об уроке"""
    try:
        lesson = await apis.mobile.get_lesson_schedule_items(
            profile_id=user.db_profile_id,
            student_id=user.db_profile["children"][0]["id"],
            lesson_id=command.args.strip()
        )
    except APIError as e:
        return await message.answer(f"❕ [<code>{e.status_code}</code>] Сервер <b>не ответил</b> на запрос, <b>ошибка</b>...\nПопробуйте позднее.")
    
    return await message.answer(
        lesson_info(lesson)
    )
