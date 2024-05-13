#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import re
from datetime import date, datetime, timedelta
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


class ScheduleInfo:
    def __init__(
            self,
            events: api.APIResponse[EventsResponse],
            user: User,
            *,
            inline: bool = False,
            exclude_marks: bool = False
    ):
        self.events = events
        self.inline = inline
        self.exclude_marks = exclude_marks
        self.user = user

        self.days: dict[date, list[Item]] = {}
        self.sort_by_date(events)

    @staticmethod
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

    def sort_by_date(self, events: api.APIResponse[EventsResponse]):
        for event in events.response.response:
            start = event.start_at
            if isinstance(start, str):
                start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=TIMEZONE)

            date = start.date()

            if date not in self.days:
                self.days[date] = []

            self.days[date].append(event)

    def gen_day_info(self, dt: date) -> str:
        settings: dict[str, bool] = self.user.db_settings.get("schedule_details", {})
        text = (
            (
                Texts.FROM_CACHE(self.events.last_cache_time)
                if self.events.is_cache
                else ""
            )
            + Texts.SCHEDULE_FOR_DAY(
                WEEKDAY=self.weekday(dt.weekday()),
                DAY=dt.strftime("%d.%m"),
            )
        )
        hints = []
        for event in self.days[dt]:
            start = event.start_at
            end = event.finish_at

            lesson_type = f"[ <b>ID</b>: <code>{event.id}</code> ]" if settings.get("show_id", False) else ""
            match event.source:
                case "ORGANIZER":
                    lesson_type = "[ <b>ЭКС*</b> ]"
                    if "ORGANIZER" not in hints:
                        hints.append("ORGANIZER")
                case "EC":
                    lesson_type = "[ <b>ВД*</b> ]"
                    if "EC" not in hints:
                        hints.append("EC")
                case "AE":
                    lesson_type = "[ <b>ДО*</b> ]"
                    if "AE" not in hints:
                        hints.append("AE")
                case "EVENTS":
                    lesson_type = "[ <b>ЛС*</b> ]"
                    if "EVENTS" not in hints:
                        hints.append("EVENTS")

            if event.source != "EVENTS":
                if not settings.get("show_other_lessons", True) and event.source != "PLAN":
                    continue

                homeworks = [
                    homework.replace("\n", "</i>; <i>")
                    for homework in event.homework.descriptions
                ] if event.homework and event.homework.descriptions else []

                event_text = (
                    f"• <a href=\"{start_with_args('lesson_' + str(event.id) + '_' + event.source)}\"><b>{event.subject_name}</b></a> "
                    f"[ <code>{start.hour:02}:{start.minute:02}-{end.hour:02}:{end.minute:02}</code> ] "
                    f"[ <code>{event.room_number}{'к.' if str(event.room_number).isdigit() else ''}</code> ] "
                    f"{lesson_type}"
                )
                if settings.get("show_theme", True) and event.lesson_name:
                    theme = event.lesson_name.replace('\n', ' ')
                    event_text += f"\n  ✕ <b>Тема</b>: <i>{theme}</i>"
                if settings.get("show_homeworks", True) and homeworks:
                    event_text += (
                        "\n  ✕ <b>ДЗ</b>: <i>"
                        + "</i>\n  ✕ <b>ДЗ</b>: <i>".join(homeworks)
                        + "</i>" + (
                            f" <b>({event.homework.materials.count_execute} выполнить)</b>"
                            if event.homework.materials and event.homework.materials.count_execute else ""
                        ) + (
                            f" <b>({event.homework.materials.count_learn} изучить)</b>"
                            if event.homework.materials and event.homework.materials.count_learn else ""
                        )
                    )
                if settings.get("show_marks", True) and event.marks and not self.exclude_marks:
                    event_text += (
                            "\n  ✕ <b>Оценки</b>: "
                            + " | ".join([
                                f'<a href="{start_with_args("mark_" + str(mark.id))}">{MARK(mark.value, mark.weight)}</a>'
                                for mark in event.marks
                            ])
                    )
                if settings.get("show_replaces", True) and event.replaced:
                    event_text += "\n  ✕ <b>Замена</b>: ✅"
                if event.cancelled:
                    event_text += "\n  ✕ <b>Отмена</b>: ✅"
            else:
                if not settings.get("show_events", True):
                    continue

                event_text = (
                        f"• <b>{event.title}</b> "
                        + (
                            f"[ <code>{start.hour:02}:{start.minute:02}-{end.hour:02}:{end.minute:02}</code> ] "
                            if not event.is_all_day else ""
                        )
                        + lesson_type
                )
                if event.description:
                    event_text += f"\n  ✕ <b>Описание</b>: <i>{event.description}</i>"
                if event.conference_link:
                    event_text += f"\n  ✕ <b>Конференция</b>: <i>{event.conference_link}</i>"
                if event.place:
                    event_text += f"\n  ✕ <b>Место</b>: <i>{event.place}</i>"

            count = len(re.findall(r"✕", event_text))
            if count > 1:
                event_text = re.sub(r"✕", r"├", event_text, count=count - 1)
            event_text = re.sub(r"✕", r"└", event_text)

            text += event_text + "\n"

        text += (
            Texts.LESSON_INFO_DETAIL(
                PREFIX="/" if not self.inline else "@OctoDiaryBot "
            )
            + (
                Texts.LESSON_DESIGNATIONS + "".join([
                    getattr(Texts.DESIGNATIONS, event_type)
                    for event_type in hints
                ])
                if hints
                else ""
            )
        )
        return text

    def inline_strings(self):
        return {
            dt.strftime("%d.%m"): self.gen_day_info(dt)
            for dt in self.days
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
        f"{file.title} (<a href='{file.link}'>ОТКРЫТЬ</a>)"
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
    return Texts.LESSON_INFO(lesson=lesson, topic=lesson.details.lesson_topic or "❌") + (
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


def mark_info_text(mark: MarkInfo) -> tuple[str, str]:
    return Texts.MARK_INFO_FULL(
        mark=mark,
        WEIGHT=pluralization_string(mark.weight, ["балл", "балла", "баллов"]),
        COMMENT=mark.comment or "❌",
        CREATED_AT=mark.updated_at.strftime("%Y-%m-%d %H:%M"),
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
    ), start_with_args(f"lesson_{mark.activity.schedule_item_id}_PLAN")


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

    response = update if is_inline else await update.bot.inline.answer(update, Texts.LOADING)

    today = get_date()
    events = await api.get_events(
        user=user,
        apis=apis,
        begin_date=today - timedelta(days=-1 * (0 - today.weekday())),
        end_date=today + timedelta(days=14 + (6 - today.weekday()))
    )

    strings = ScheduleInfo(events, user, inline=is_inline).inline_strings()
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
        lesson_type: Optional[str] = None,
        *,
        is_inline: bool = False
):
    """Get lesson information"""

    response = update if is_inline else await update.bot.inline.answer(update, Texts.LOADING)

    try:
        lesson = await api.get_schedule_item(
            user=user,
            apis=apis,
            lesson_id=int(command.args.strip() if command else lesson_id),
            lesson_type=lesson_type if lesson_type else "PLAN"
        )
    except Exception:
        return await update.answer(Texts.LESSON_NOT_FOUND)

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

    text, button_url = mark_info_text(mark_data.response)

    await update.bot.inline.answer(
        response,
        response=text,
        reply_markup=[
            [
                {
                    "text": Texts.Buttons.LESSON_INFO,
                    "url": button_url
                }
            ],
            [
                {
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
            ]
        ]
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)
