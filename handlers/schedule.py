#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import datetime, timedelta
from typing import Optional

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import api
from apis import APIs
from database import User
from handlers.router import router
from inline.types import AdditionalButtons
from octodiary import types
from octodiary.exceptions import APIError
from octodiary.types.mobile import EventsResponse
from octodiary.types.mobile.events import Item
from utils.additional_models import MarkInfo
from utils.filters import apis_and_user
from utils.other import TIMEZONE, get_date, handler, pluralization_string, sort_dict_by_date, start_with_args
from utils.other import mark as MARK
from utils.texts import Texts

LessonScheduleItem = types.mobile.LessonScheduleItem
LessonHomework = types.mobile.lesson_schedule_item.LessonHomework
Mark = types.mobile.lesson_schedule_item.Mark


def day_schedule_info(events: api.APIResponse[EventsResponse], *, inline: bool = False, exclude_marks: bool = False):
    days_lessons = {}

    def weekday(x):
        return {
            0: "понедельник",
            1: "вторник",
            2: "среду",
            3: "четверг",
            4: "пятницу",
            5: "субботу",
            6: "воскресенье"
        }[int(x)]

    available_other_source: dict[str, list[str]] = {}

    for event in events.response.response:
        is_event = False

        start = event.start_at
        end = event.finish_at

        date = start.date()
        date_str = f"{date.day:02}.{date.month:02}/{date.weekday()}"

        if date_str not in days_lessons:
            days_lessons[date_str] = []

        lesson_info = f"[ <b>ID</b>: <code>{event.id}</code> ]"

        if date_str not in available_other_source:
            available_other_source[date_str] = []

        match event.source:
            case "ORGANIZER":
                lesson_info = "[ <b>ЭКС*</b> ]"
                available_other_source[date_str] += ["ORGANIZER"]
            case "EC":
                lesson_info = "[ <b>ВД*</b> ]"
                available_other_source[date_str] += ["EC"]
            case "AE":
                lesson_info = "[ <b>ДО*</b> ]"
                available_other_source[date_str] += ["AE"]
            case "EVENTS":
                lesson_info = "[ <b>ЛС*</b> ]"
                available_other_source[date_str] += ["EVENTS"]
                is_event = True

        if not is_event:
            homeworks = [
                homework.replace("\n", "</code>; <code>")
                for homework in event.homework.descriptions
            ] if event.homework and event.homework.descriptions else []

            days_lessons[date_str].append(
                (
                    f"• <b>{event.subject_name}</b> "
                    f"[ <code>{start.hour:02}:{start.minute:02}-{end.hour:02}:{end.minute:02}</code> ] [ <code>{event.room_number}{'к.' if str(event.room_number).isdigit() else ''}</code> ] "
                )
                + lesson_info
                + (
                    f"\n  {'├' if event.cancelled or homeworks or event.marks else '└'} <b>Замена</b>: ✅" if event.replaced else "")
                + (f"\n  {'├' if homeworks or event.marks else '└'} <b>Отмена</b>: ✅" if event.cancelled else "")
                + (
                    (
                            f"\n  {'├' if homeworks else '└'} <b>Оценки</b>: " + " | ".join(
                                [f"<code>{MARK(mark.value, mark.weight)}</code>" for mark in event.marks])
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
        else:
            days_lessons[date_str].append(
                (
                    f"• <b>{event.title}</b> "
                ) + (
                    f"[ <code>{start.hour:02}:{start.minute:02}-{end.hour:02}:{end.minute:02}</code> ] "
                    if not event.is_all_day else ""
                ) + lesson_info + (
                    f"\n  {'├' if event.conference_link or event.place else '└'} <b>Описание</b>: {event.description}" if event.description else ""
                ) + (
                    (
                        f"\n  {'├' if event.place else '└'} <b>Конференция</b>: {event.conference_link}"
                    ) if event.conference_link else ""
                ) + (
                    (
                        f"\n  └ <b>Место</b>: {event.place}"
                    ) if event.place else ""
                )
            )

    return {
        (Texts.FROM_CACHE(events.last_cache_time) if events.is_cache else "") + date_str.split("/")[0]: Texts.SCHEDULE_FOR_DAY(
            WEEKDAY=date_str.split("/")[0],
            DAY=weekday(date_str.split("/")[1]),
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
        MARK_INFO_URL=start_with_args("mark_" + str(mark.id)),
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


def lesson_info(lesson: LessonScheduleItem) -> str:
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


def mark_info_text(mark: MarkInfo) -> str:
    return Texts.MARK_INFO_FULL(
        mark=mark,
        WEIGHT=pluralization_string(mark.weight, ["балл", "балла", "баллов"]),
        COMMENT=mark.comment or "❌",
        CREATED_AT=mark.updated_at.strftime("%d.%m.%Y %H:%M"),
        LESSON_INFO_URL=start_with_args(f"lesson_{mark.activity.schedule_item_id}_PLAN"),
        IS_EXAM_EMOJI="❗️" if mark.is_exam else "",
    ) + (
        Texts.MARK_INFO_DETAILS.STATISTICS(
            TOTAL_STUDENTS_COUNT=pluralization_string(
                mark.class_results.total_students,
                ["ученик", "ученика", "учеников"]
            )
        ) + "<blockquote>" + (
            "\n".join([
                (
                    f"<b>{mark_stat.mark_value.five}</b> "
                    f"{'▓'*round(mark_stat.percentage_of_students/10)}"
                    f"{'▒'*(10-round(mark_stat.percentage_of_students/10))}"
                    f" <b>({mark_stat.percentage_of_students}%, {mark_stat.number_of_students} уч.)</b>"
                )
                for mark_stat in mark.class_results.marks_distributions
            ])
        ) + "</blockquote>"
    )


@router.message(Command("schedule"))
@router.message(F.text == Texts.Buttons.SCHEDULE, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def schedule(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        *,
        is_inline: bool = False
):
    """Get schedule information"""

    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    today = get_date()
    events = await api.get_events(
        user=user,
        apis=apis,
        begin_date=today - timedelta(days=-1 * (0 - today.weekday())),
        end_date=today + timedelta(days=14 + (6 - today.weekday()))
    )

    strings = day_schedule_info(events, inline=is_inline)
    await update.bot.inline.list(
        response,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": schedule,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": is_inline
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(strings),
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)


@router.message(Command("lesson"))
@handler()
@apis_and_user
async def get_lesson_info(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        command: CommandObject = None,
        lesson_id: Optional[str] = None,
        *,
        is_inline: bool = False
):
    """Get lesson information"""

    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    lesson = await api.get_schedule_item(
        user=user,
        apis=apis,
        lesson_id=int(command.args.strip() if command else lesson_id)
    )

    await update.bot.inline.answer(
        response,
        response=lesson_info(lesson),
        reply_markup={
            "text": Texts.Buttons.UPDATE,
            "callback": get_lesson_info,
            "kwargs": {
                "apis": apis,
                "user": user,
                "lesson_id": lesson_id,
                "is_inline": is_inline
            },
            "reusable": True,
            "disable_deadline": True
        }

    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)


@router.message(Command("mark"))
@handler()
@apis_and_user
async def get_mark_info(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        command: CommandObject = None,
        mark_id: Optional[str] = None,
        *,
        is_inline: bool = False
):
    """Get mark information"""

    response = update if is_inline else await update.bot.inline.answer(update, Texts.LOADING)

    try:
        mark_data = await api.get_mark(user, apis, mark_id if mark_id else int(command.args.strip()))
    except Exception:
        return await update.answer(Texts.MARK_NOT_FOUND)

    await update.bot.inline.answer(
        response,
        response=mark_info_text(mark_data.response),
        reply_markup={
            "text": Texts.Buttons.UPDATE,
            "callback": get_mark_info,
            "kwargs": {
                "apis": apis,
                "user": user,
                "mark_id": mark_id,
                "command": command
            },
            "reusable": True,
            "disable_deadline": True
        }
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)
