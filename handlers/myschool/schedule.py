#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date, datetime, timedelta

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from database import User
from handlers.myschool.router import APIs, MySchool, MySchoolUser, isMySchoolUser, router
from octodiary.exceptions import APIError
from octodiary.types.myschool.mobile import EventsResponse
from octodiary.types.myschool.mobile.lesson_schedule_items import (
    LessonHomework,
    LessonScheduleItems,
    Mark,
)
from utils.other import handler, pluralization_string, sort_dict_by_date
from utils.other import mark as MARK
from utils.texts import Texts


def day_schedule_info(events: EventsResponse, from_db, *, inline: bool = False, exclude_marks: bool = False):
    days_lessons = {}
    def weekday(x):
        return {0: "понедельник", 1: "вторник", 2: "среду", 3: "четверг", 4: "пятницу", 5: "субботу", 6: "воскресенье"}[int(x)]

    available_other_source: dict[str, list[str]] = {}

    for event in events.response:

        start = datetime.strptime(event.start_at, "%Y-%m-%dT%H:%M:%S%z")
        end = datetime.strptime(event.finish_at, "%Y-%m-%dT%H:%M:%S%z")

        date = start.date()
        date_str = f"{date.day:02}.{date.month:02}/{date.weekday()}"

        if date_str not in days_lessons:
            days_lessons[date_str] = []

        lesson_info = f"[ <b>ID</b>: <code>{event.id}</code> ]"
        
        
        if not date_str in available_other_source:
            available_other_source[date_str] = []

        if event.source == "EC":
            available_other_source[date_str] += ["EC"]
            lesson_info = "[ <b>ВД*</b> ]"
        elif event.source == "AE":
            available_other_source[date_str] += ["AE"]
            lesson_info = "[ <b>ДО*</b> ]"
        elif event.source == "ORGANIZER":
            available_other_source[date_str] += ["ORGANIZER"]
            lesson_info = "[ <b>ЭКС*</b> ]"


        homeworks = [
            homework.replace("\n", "</code>; <code>")
            for homework in event.homework.descriptions
        ] if event.homework and event.homework.descriptions else []

        days_lessons[date_str].append(
            (
                f"• <b>{event.subject_name}</b> "
                f"[ <code>{start.hour:02}:{start.minute:02}-{end.hour:02}:{end.minute:02}</code> ] "
            )
            + lesson_info
            + (f"\n  {'├' if event.cancelled or homeworks or event.marks else '└'} <b>Замена</b>: ✅" if event.replaced else "")
            + (f"\n  {'├' if homeworks or event.marks else '└'} <b>Отмена</b>: ✅" if event.cancelled else "")
            + (
                (
                    f"\n  {'├' if homeworks else '└'} <b>Оценки</b>: " + " | ".join([f"<code>{MARK(mark.value, mark.weight)}</code>" for mark in event.marks])
                ) if event.marks and not exclude_marks else ""
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
        date_str.split("/")[0]: Texts.SCHEDULE_FOR_DAY(
            WEEKDAY=date_str.split("/")[0],
            DAY=weekday(date_str.split("/")[1]),
            from_db=from_db
        ) + "\n".join(lessons) + Texts.LESSON_INFO_DETAIL(
            PREFIX="/" if not inline else "@OctoDiaryBot "
        ) + (
            Texts.LESSON_DESIGNATIONS + "".join([
                getattr(Texts.DESIGNATIONS, event_type)
                for event_type in event_types
            ])
            if (
                event_types := list(set(
                    available_other_source.get(date_str, [])
                ))
            )
            else ""
        )
        for date_str, lessons in days_lessons.items()
    }

def mark_info(mark: Mark) -> str:
    return Texts.MARK_INFO_SECOND(
        VALUE=MARK(mark.value, mark.weight),
        CONTROL_FORM_NAME=mark.control_form_name,
        WEIGHT=pluralization_string(mark.weight, ["балл", "балла", "баллов"]),
        IS_EXAM_EMOJI="❗️" if mark.is_exam else "",
        UPDATED_AT=mark.updated_at.strftime("%d.%m.%Y %H:%M"),
        COMMENT=mark.comment or "❌"
    )

def homework_info(homework: LessonHomework) -> str:
    files = [
        f"<a href='{file.link}'>{file.title}</a>"
        for material in homework.materials
        for file in material.items
    ] if homework.materials else []

    return Texts.HOMEWORK_INFO(
        HOMEWORK=homework.homework,
        UPLOADED_FILES="✅" if files else "❌",
    ) + (
        (
            ("\n   ├ " if len(files) > 1 else "")
            + "\n   ├ ".join(files[:-1])
            + f"\n   └ {files[-1]}"
        ) if files else ""
    )


def lesson_info(lesson: LessonScheduleItems) -> str:
    return Texts.LESSON_INFO(lesson=lesson, topic=lesson.details.lesson_topic.strip() or "❌") + (
        (
            Texts.LESSON_INFO_DETAILS.THEMES + (
                "\n".join([
                    Texts.THEME_FRAME(
                        theme=theme.title
                    )
                    for theme in lesson.details.theme.theme_frames
                    if theme.title
                ])
            )
        ) if lesson.details and lesson.details.theme.theme_frames else ""
    ) + (
        (
            Texts.LESSON_INFO_DETAILS.MARKS + (
                "\n".join([mark_info(mark) for mark in lesson.marks])
            )
        ) if lesson.marks else ""
    ) + (
        (
            Texts.LESSON_INFO_DETAILS.HOMEWORKS + (
                "\n".join([homework_info(homework) for homework in lesson.lesson_homeworks])
            )
        ) if lesson.lesson_homeworks else ""
    )


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("schedule")
)
@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == Texts.Buttons.SCHEDULE,
    F.chat.type == ChatType.PRIVATE
)
@handler()
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
                today + timedelta(days= 14+(6 - today.weekday()))
            )
        )
    except APIError:
        events = user.db_events
        from_db = Texts.FROM_DB

    strings = day_schedule_info(events, from_db)
    await message.bot.inline.list(
        message, **sort_dict_by_date(strings), row_width=5,
    )


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("lesson")
)
@handler()
async def get_lesson_info(message: Message, apis: APIs, user: User, command: CommandObject):
    """Получить информацию o6 уроке"""
    lesson = await apis.mobile.get_lesson_schedule_items(
        profile_id=user.db_profile_id,
        student_id=user.db_profile["children"][0]["id"],
        lesson_id=command.args.strip()
    )

    return await message.answer(
        lesson_info(lesson)
    )
