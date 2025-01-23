#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import datetime
import random
import re
import time
import typing
import uuid
from datetime import timedelta

from aiogram import Router, F, types, Bot
from aiogram.filters import Command, CommandObject
from octodiary.types.mobile import SubjectsMarks, Marks, EventsResponse, LessonScheduleItem
from pydantic import BaseModel

from core.keyboards.inline import DIARY, BACK_BUTTON, CALC_MARKS
from core.misc.additional_models import MarkInfo, Homeworks, HomeworkItem
from core.misc.texts import Texts
from core.misc.utils import get_date, get_week_for_date, MONTH_NAME_NUMERALS, pluralization_string, start_with_args, \
    fmark, chunks, WEEKDAY, escape_html, parse_time, parse_date_iso
from core.services.api import UserData, DataType
from core.services.database import database
from core.misc.inline.types import AdditionalButtons

router = Router(name="Diary")


@router.message(Command("diary", "d"))
@router.message(F.text == Texts.Diary.COMMAND)
@router.callback_query(F.data == "diary:root:back")
async def diary_cmd(update: types.Message | types.CallbackQuery | types.ChosenInlineResult, bot: Bot):
    user = database.user(update.from_user.id)
    if not user.token:
        await update.answer(
            Texts.NOT_AUTHORIZED
        )
        return

    if (inline := getattr(update, "inline_message_id", None)) is not None:
        await update.answer()
        await bot.edit_message_text(
            inline_message_id=inline,
            text=Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS)),
            reply_markup=DIARY
        )
        return

    await (update.answer if isinstance(update, types.Message) else update.message.edit_text)(
        Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS)),
        reply_markup=DIARY
    )


@router.callback_query(
    F.data.in_(
        list(Texts.Diary.Commands.keys())
        + list(map(lambda x: f"{x}:upd", list(Texts.Diary.Commands.keys())))
    )
)
async def diary_callback(update: types.CallbackQuery, bot: Bot):
    inline = update.inline_message_id
    user = database.user(update.from_user.id)
    today = get_date()
    is_update = update.data.endswith(":upd")

    if update.data.startswith("diary:marks_by_subject"):
        user_data = UserData(user, user.apis)
        try:
            marks_by_subject: SubjectsMarks = await user_data.get(DataType.MARKS_BY_SUBJECT)
        except: # noqa
            marks_by_subject: SubjectsMarks = await user_data.get_cached(DataType.MARKS_BY_SUBJECT)
            cache = True

        info = "\n".join(
            list(dict(sorted({
                Texts.Diary.MarksBySubject.SUBJECT(
                    AVERAGE=period.value or "—",
                    NAME=(
                        sub.subject_name
                        .replace(Texts.Diary.MarksBySubject.OBZR, Texts.Diary.MarksBySubject.OBZR_SHORT)
                        .replace(Texts.Diary.MarksBySubject.PHIZ_KULTURA, Texts.Diary.MarksBySubject.PHIZ_KULTURA_SHORT)
                    ),
                    MARKS_COUNT=pluralization_string(period.count, ["оценка", "оценки", "оценок"])
                ): period.value or "0"
                for sub in marks_by_subject.payload
                for period in sub.periods
                if datetime.date.fromisoformat(period.start_iso) <= today <= datetime.date.fromisoformat(period.end_iso)
            }.items(), key=lambda x: float(x[1]), reverse=True)).keys())
        )

        await bot.inline.list(
            update=update,
            strings={
                Texts.Buttons.HOME: (
                    Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS))
                    + Texts.Diary.MarksBySubject.TEXT(
                        Texts.Diary.Commands[update.data.replace(":upd", "")],
                        SUBJECTS=info
                    )
                )
            } | {
                (
                    sub.subject_name
                    .replace(Texts.Diary.MarksBySubject.OBZR, Texts.Diary.MarksBySubject.OBZR_SHORT)
                    .replace(Texts.Diary.MarksBySubject.PHIZ_KULTURA, Texts.Diary.MarksBySubject.PHIZ_KULTURA_SHORT)
                ): (
                    Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS))
                    + Texts.Diary.TYPE(Texts.Diary.Commands[update.data.replace(":upd", "")])
                    + Texts.Diary.MarksBySubject.SUBJECT_ALL(
                        SUBJECT_NAME=sub.subject_name,
                        AVERAGE_BY_ALL=sub.average_by_all,
                        PERIODS="\n".join([
                            Texts.Diary.MarksBySubject.PERIOD(
                                TITLE=period.title,
                                START=period.start,
                                END=period.end,
                                AVERAGE=period.value or "❌",
                                DYNAMIC=(
                                    "🔺" if period.dynamic == "UP" else "🔻" if period.dynamic == "DOWN" else ""
                                ) if not period.fixed_value else "",
                                FIXED=Texts.Diary.MarksBySubject.FIXED(
                                    Texts.Diary.MarksBySubject.EMOJIS[period.fixed_value]
                                ) if period.fixed_value else "",
                                GOALS=Texts.Diary.MarksBySubject.GOAL(
                                    ROUND=period.target.round,
                                    VALUE=period.target.value,
                                    NEED=Texts.OR.join([
                                        fmark(str(method.value), method.weight) + f"[{method.remain} шт.]"
                                        for method in period.target.paths
                                    ])
                                ) if (
                                        user.db_settings.get("goals", True)
                                        and period.target
                                        and period.target.round
                                        and period.target.paths
                                ) else "",
                                COUNT=str(period.count or "❌"),
                                MARKS=user.db_settings.get("marks_sep", " • ").join([
                                    f"<a href=\"{start_with_args('mark_' + str(mark.id))}\">{fmark(mark.value, mark.weight)}</a>"
                                    for mark in period.marks
                                ]) if period.marks else "❌"
                            )
                            for period in sub.periods
                        ])
                    )
                )
                for sub in marks_by_subject.payload
            },
            additional_buttons=AdditionalButtons(
                below_buttons=[
                    [
                        {
                            "text": Texts.Buttons.CALCULATOR,
                            "url": start_with_args("calc")
                        } if not inline else {
                            "text": Texts.Buttons.CALCULATOR,
                            "switch_inline_query_current_chat": ""
                        }
                    ],
                    [
                        {
                            "text": Texts.Buttons.UPDATE,
                            "callback_data": update.data.replace(":upd", "") + ":upd",
                        },
                        {
                            "text": Texts.Buttons.BACK,
                            "callback_data": "diary:root:back"
                        }
                    ]
                ]
            ),
            row_width=2
        )
        if is_update:
            await update.answer(Texts.UPDATED)

        return

    weeks = [
        (week, today in week)
        for i in range(-user.db_settings.get("weeks_offset", 2), user.db_settings.get("weeks_offset", 2) + 1)
        if (week := get_week_for_date(today + timedelta(weeks=i)))
    ]

    await bot.edit_message_text(
        inline_message_id=inline,
        chat_id=update.message.chat.id if update.message else None,
        message_id=update.message.message_id if update.message else None,
        text=(
                 Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS))
                 + Texts.Diary.CHOOSE_WEEK(Texts.Diary.Commands[update.data.replace(":upd", "")])
        ),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=("● " if current else "") + (
                            (
                                f"{week[0].strftime('%d.%m')} — {week[-1].strftime('%d.%m')}"
                                if week[0].year == week[-1].year
                                else f"{week[0].strftime('%d.%m.%Y')} — {week[-1].strftime('%d.%m.%Y')}"
                            ) if user.db_settings.get("week_format", "full") == "short" else (
                                (
                                    f"{week[0].day} {MONTH_NAME_NUMERALS[week[0].month].lower()}"
                                    f" — {week[-1].day} {MONTH_NAME_NUMERALS[week[-1].month].lower()}"
                                ) if week[0].year == week[-1].year else (
                                    f"{week[0].day} {MONTH_NAME_NUMERALS[week[0].month].lower()} {week[0].year}"
                                    f" — {week[-1].day} {MONTH_NAME_NUMERALS[week[-1].month].lower()} {week[-1].year}"
                                )
                            )
                        ) + (" ●" if current else ""),
                        callback_data=f"{update.data.replace(":upd", "")}:{week[0].isoformat()}"
                    )
                ]
                for week, current in weeks
            ] + BACK_BUTTON("diary:root")
        )
    )


@router.callback_query(F.data.regexp(r"diary:(.*):(.*):upd"))
async def diary_week_update(call: types.CallbackQuery, bot: Bot):
    await diary_week(call, bot, re.match(r"diary:(.*):(.*)", call.data.removesuffix(":upd")), upd=True)


@router.callback_query(F.data.regexp(r"diary:(.*):(.*)").as_("match"), F.data.not_contains("upd"))
async def diary_week(call: types.CallbackQuery, bot: Bot, match: re.Match, upd: bool = False):
    user = database.user(call.from_user.id)
    user_data = UserData(user, user.apis)

    today = get_date()
    week = []
    week_date = None
    if re.match(r"\d{4}(.\d{2}){2}", match.group(2)):
        week_date = datetime.date.fromisoformat(match.group(2))
        week = get_week_for_date(week_date)

    match match.group(1):
        case "marks_by_date":
            try:
                response: Marks = await user_data.get(DataType.MARKS_BY_DATE, from_date=week[0], to_date=week[-1])
            except: # noqa
                cached: dict = await user_data.get_cached(DataType.MARKS_BY_DATE, raw=True)
                if not (r := cached.get(week[0].isoformat(), None)):
                    ...
                    return

                print(r)
                response = Marks.model_validate(r)
                cache = True

            await bot.inline.list(
                update=call,
                strings={
                    date.strftime("%d.%m"): Texts.Diary.BASE(
                        random.choice(Texts.Diary.EMOJIS)
                    ) + Texts.Diary.MarksByDate.TEXT(
                        Texts.Diary.Commands["diary:marks_by_date"],
                        DATE=f"{WEEKDAY[date.weekday()]}, {date.day} {MONTH_NAME_NUMERALS[date.month].lower()}",
                        SHORT_DATE=date.strftime("%d.%m.%Y"),
                        MARKS=("\n".join([
                            Texts.Diary.MarksByDate.MARK(
                                SUBJECT_NAME=mark.subject_name,
                                MARK_URL=start_with_args("mark_" + str(mark.id)),
                                MARK=fmark(mark.value, mark.weight),
                                CONTROL_FORM_NAME=mark.control_form_name,
                                IS_EXAM_EMOJI="❗️" if mark.is_exam else "",
                                MODE="выставления" if mark.updated_at == mark.created_at else "изменения",
                                UPDATED_AT=mark.updated_at.replace("T", " ")[:-3],
                                COMMENT=(
                                    escape_html(mark.comment or "")
                                ) or "❌"
                            )
                            for mark in response.payload
                            if mark.date == date
                        ])) or Texts.EMPTY(random.choice(["🫥", "😶‍🌫️", "😶", "🫠", "🫣"]))
                    )
                    for date in (week[:-1] if week[-1].isoformat() + '"' not in str(response) else week)
                },
                additional_buttons=AdditionalButtons(
                    below_buttons=[
                        [
                            {
                                "text": Texts.Diary.PREVIOUS_WEEK,
                                "callback_data": f"diary:{match.group(1)}:{(week_date + timedelta(days=-7)).isoformat()}",
                            },
                            {
                                "text": Texts.Diary.NEXT_WEEK,
                                "callback_data": f"diary:{match.group(1)}:{(week_date + timedelta(days=7)).isoformat()}",
                            }
                        ],
                        [
                            {
                                "text": Texts.Buttons.UPDATE,
                                "callback_data": call.data.replace(":upd", "") + ":upd",
                            },
                            {
                                "text": Texts.Buttons.BACK,
                                "callback_data": "diary:root:back"
                            }
                        ],
                    ]
                ),
                row_width=6,
                current_page=today.strftime("%d.%m") if today in (week[:-1] if week[-1].isoformat() + '"' not in str(response) else week) else 1,
                disable_web_page_preview=True,
            )
            if upd:
                await call.answer(Texts.UPDATED)

        case "schedule":
            try:
                response: EventsResponse = await user_data.get(DataType.EVENTS, begin_date=week[0], end_date=week[-1])
            except: # noqa
                cached: dict = await user_data.get_cached(DataType.EVENTS, raw=True)
                if not (r := cached.get(week[0].isoformat(), None)):
                    ...
                    return
                print(r)
                response: EventsResponse = EventsResponse.model_validate(r)
                cache = True

            new_format: bool = user.db_settings.get("schedule_new_format", True)
            if new_format:
                strings = {
                    date.strftime("%d.%m"): Texts.Diary.BASE(
                        random.choice(Texts.Diary.EMOJIS)
                    ) + Texts.Diary.Schedule.New.TEXT(
                        Texts.Diary.Commands["diary:schedule"],
                        DATE=f"{WEEKDAY[date.weekday()]}, {date.day} {MONTH_NAME_NUMERALS[date.month].lower()}",
                        SHORT_DATE=date.strftime("%d.%m.%Y"),
                        EVENTS=("\n".join([
                            Texts.Diary.Schedule.New.EVENT(
                                TITLE=escape_html(ev.title if ev.title else ev.subject_name),
                                START=parse_time(str(ev.start_at), seconds=False),
                                END=parse_time(str(ev.finish_at), seconds=False),
                                ITEM_LINK=start_with_args("lesson_" + str(ev.id) + f"_{ev.source}"),
                                ITEMS="\n".join(
                                    [
                                        getattr(Texts.Diary.Schedule.New.ITEMS, item_name)(x)
                                        for item_name in Texts.Diary.Schedule.New.ITEMS
                                        if item_name in user.db_settings.get("sch_items", [
                                            "type", "marks", "homeworks", "room"
                                        ]) and (x := (
                                            (
                                                (" • ".join([
                                                    escape_html(homework.replace("\n", "; ").replace("\r", ""))
                                                    for homework in ev.homework.descriptions
                                                    if ev.homework and ev.homework.descriptions and homework
                                                ])) + (
                                                    f" ({ev.homework.materials.count_learn} изучить)"
                                                    if ev.homework and ev.homework.materials and ev.homework.materials.count_learn
                                                    else ""
                                                ) + (
                                                    f" ({ev.homework.materials.count_execute} пройти)"
                                                    if ev.homework and ev.homework.materials and ev.homework.materials.count_execute
                                                    else ""
                                                )
                                            )
                                            if item_name == "homeworks" and ev.homework
                                            else (
                                                user.db_settings.get("marks_sep", " • ").join([
                                                    f"<a href='{start_with_args('mark_' + str(mark.id))}'>{fmark(mark.value, mark.weight)}</a>"
                                                    for mark in ev.marks
                                                ])
                                            ) if item_name == "marks" and ev.marks
                                            else (
                                                f"{ev.room_number} ({ev.room_name})"
                                                if ev.room_name != ev.room_number
                                                else ev.room_number
                                            ) if item_name == "room"
                                            else (
                                                {
                                                    "PLAN": "",
                                                    "EC": "Внеурочная деятельность",
                                                    "ORGANIZER": "Экскурсия",
                                                    "AE": "Дополнительное образование",
                                                }[ev.source]
                                            ) if item_name == "type"
                                            else (
                                                " • ".join([
                                                    escape_html(ev.lesson_name or ""),
                                                    escape_html(ev.lesson_theme or ""),
                                                ])
                                            ) if item_name == "theme" and (ev.lesson_name or ev.lesson_theme)
                                            else getattr(ev, item_name, "")
                                        ))
                                    ]
                                )
                            ) if ev.source != "EVENTS" else Texts.Diary.Schedule.New.EVENT(
                                TITLE=escape_html(ev.title),
                                START=parse_time(str(ev.start_at), seconds=False) if not ev.is_all_day else "Весь день",
                                END=parse_time(str(ev.finish_at), seconds=False) if not ev.is_all_day else "",
                                ITEMS="\n".join(
                                    [
                                        getattr(Texts.Diary.Schedule.New.ITEMS, item_name)(x)
                                        for item_name in Texts.Diary.Schedule.New.ITEMS
                                        if item_name in user.db_settings.get("sch_items", [
                                            "",
                                        ]) and (x := (
                                            escape_html(ev.description[:300]) + "..."
                                            if item_name == "description"
                                            else escape_html(ev.get(item_name, ""))
                                        ))
                                    ]
                                )
                            )
                            for ev in response.response
                            if parse_date_iso(
                                ev.start_at
                            ) == date.isoformat()
                            and (
                                ev.source == "PLAN"
                                or (
                                   ev.source == "EVENTS"
                                   and user.db_settings.get("schedule_show_custom_events", True)
                                ) or (
                                    user.db_settings.get("schedule_show_other_events", True)
                                )
                            )
                        ])) or Texts.EMPTY(random.choice(["🫥", "😶‍🌫️", "😶", "🫠", "🫣"]))
                    ) if user.db_settings.get("schedule_show_custom_events", True) else ""
                    for date in (week[:-1] if week[-1].isoformat() + '"' not in str(response) else week)
                }
            else:
                await call.answer("Временно недоступно :(", show_alert=True)
                return

                strings = {
                    date.strftime("%d.%m"): Texts.Diary.BASE(
                        random.choice(Texts.Diary.EMOJIS)
                    ) + Texts.Diary.Schedule.New.TEXT(
                        Texts.Diary.Commands["diary:schedule"],
                        DATE=f"{WEEKDAY[date.weekday()]}, {date.day} {MONTH_NAME_NUMERALS[date.month].lower()}",
                        SHORT_DATE=date.strftime("%d.%m.%Y"),
                        EVENTS=("\n".join([
                            Texts.Diary.Schedule.New.EVENT(
                                EVENT_NAME=ev.event_name,
                                EVENT_URL=start_with_args("event_" + str(ev.id)),
                                EVENT_TYPE=ev.event_type,
                                EVENT_DATE=ev.event_date.replace("T", " ")[:-3],
                                EVENT_LOCATION=ev.event_location
                            )
                            for ev in response.response
                            if ev.date == date
                        ])) or Texts.EMPTY(random.choice(["🫥", "😶‍🌫️", "😶", "🫠", "🫣"]))
                    )
                    for date in (week[:-1] if week[-1].isoformat() + '"' not in str(response) else week)
                }

            await bot.inline.list(
                update=call,
                strings=strings,
                additional_buttons=AdditionalButtons(
                    below_buttons=[
                        [
                            {
                                "text": Texts.Diary.PREVIOUS_WEEK,
                                "callback_data": f"diary:{match.group(1)}:{(week_date + timedelta(days=-7)).isoformat()}",
                            },
                            {
                                "text": Texts.Diary.NEXT_WEEK,
                                "callback_data": f"diary:{match.group(1)}:{(week_date + timedelta(days=7)).isoformat()}",
                            }
                        ],
                        [
                            {
                                "text": Texts.Buttons.UPDATE,
                                "callback_data": call.data.replace(":upd", "") + ":upd",
                            },
                            {
                                "text": Texts.Buttons.BACK,
                                "callback_data": "diary:root:back"
                            }
                        ],
                    ]
                ),
                row_width=6,
                current_page=today.strftime("%d.%m") if today in (
                    week[:-1]
                    if week[-1].isoformat() + '"' not in str(response)
                    else week
                ) else 1,
            )
            if upd:
                await call.answer(Texts.UPDATED)

        case "homeworks":
            try:
                response: Homeworks = await user_data.get(DataType.HOMEWORKS, from_date=week[0], to_date=week[-1])
            except: # noqa
                cached: dict = await user_data.get_cached(DataType.HOMEWORKS, raw=True)
                if not (r := cached.get(week[0].isoformat(), None)):
                    ...
                    return
                print(r)
                response: Homeworks = Homeworks.model_validate(r)
                cache = True

            homeworks: dict[str, dict[str, list[HomeworkItem]]] = {}
            for hw in response.payload:
                date = hw.date.strftime("%d.%m")
                if date not in homeworks:
                    homeworks[date] = {}
                if hw.subject_name not in homeworks[date]:
                    homeworks[date][hw.subject_name] = []

                homeworks[date][hw.subject_name].append(hw)

            if user.db_settings.get("tests_buttons", True):
                tests = {
                    date: [
                        [
                            {
                                "text": item.title[:40] + "..." if len(item.title) > 40 else item.title,
                                ("web_app" if user.db_settings.get("tests_in_web_app", False) else "url"): (
                                    await user_data.get(
                                        DataType.MATERIAL_LAUNCH_LINK,
                                        material_id=item.uuid,
                                        homework_entry_id=hw.homework_entry_id
                                    )  # [i.url for i in item.urls if i.url_type in ["launch", "player"]][0]
                                )
                            }
                        ]
                        for sub in subjects
                        for hw in subjects[sub]
                        for material in hw.additional_materials
                        for item in material.items
                        if item.selected_mode == "execute"
                        and material.action_name == "Пройти"
                    ]
                    for date, subjects in homeworks.items()
                }
            else:
                tests = {}

            for date, items in tests.copy().items():
                if items:
                    tests[date] = [
                        [
                            {
                                "text": Texts.Buttons.WEB_AUTH_TESTS,
                                ("web_app" if user.db_settings.get("tests_in_web_app", False) else "url"): (
                                    "https://uchebnik.mos.ru/main"
                                )
                            }
                        ]
                    ] + items

            await bot.inline.list(
                update=call,
                strings={
                    date.strftime("%d.%m"): Texts.Diary.BASE(
                        random.choice(Texts.Diary.EMOJIS)
                    ) + Texts.Diary.Homeworks.TEXT(
                        Texts.Diary.Commands["diary:homeworks"],
                        DATE=f"{WEEKDAY[date.weekday()]}, {date.day} {MONTH_NAME_NUMERALS[date.month].lower()}",
                        SHORT_DATE=date.strftime("%d.%m.%Y"),
                        SUBJECTS=("\n".join([
                            Texts.Diary.Homeworks.SUBJECT(
                                NAME=sub,
                                HOMEWORKS=("\n".join([
                                    Texts.Diary.Homeworks.HOMEWORK(
                                        DONE=(
                                            {True: "(✅) ", False: "(❎) "}[hw.is_done]
                                        ) if user.db_settings.get("homeworks", {}).get("show_status", False) else "",
                                        TEXT=hw.homework,
                                        MATERIALS="".join([
                                            Texts.Diary.Homeworks.MATERIAL(
                                                TYPE=material.action_name,
                                                NAME=item.title,
                                                URL=(
                                                    item.link
                                                    if item.link
                                                    else [i.url for i in item.urls if i.url_type in ["launch", "player"]][0]
                                                )
                                            )
                                            for material in hw.additional_materials
                                            for item in material.items
                                        ])
                                    )
                                    for hw in hws
                                ]))
                            )
                            for sub, hws in homeworks.get(date.strftime("%d.%m"), {}).items()
                        ])) or Texts.EMPTY(random.choice(["🫥", "😶‍🌫️", "😶", "🫠", "🫣"]))
                    ) + (
                        Texts.Diary.TESTS_NEED_AUTH
                        if tests.get(date.strftime("%d.%m"))
                        and user.db_settings.get("tests_buttons", False)
                        else ""
                    )
                    for date in (week[:-1] if week[-1].strftime("%d.%m") not in homeworks else week)
                },
                additional_buttons=AdditionalButtons(
                    below_buttons=[
                        [
                            {
                                "text": Texts.Diary.PREVIOUS_WEEK,
                                "callback_data": f"diary:{match.group(1)}:{(week_date + timedelta(days=-7)).isoformat()}",
                            },
                            {
                                "text": Texts.Diary.NEXT_WEEK,
                                "callback_data": f"diary:{match.group(1)}:{(week_date + timedelta(days=7)).isoformat()}",
                            }
                        ],
                        [
                            {
                                "text": Texts.Buttons.UPDATE,
                                "callback_data": call.data.replace(":upd", "") + ":upd",
                            },
                            {
                                "text": Texts.Buttons.BACK,
                                "callback_data": "diary:root:back"
                            }
                        ],
                    ],
                    below_buttons_f=tests if user.db_settings.get("tests_buttons", False) else {},
                ),
                row_width=6,
                current_page=today.strftime("%d.%m") if today in (week[:-1] if week[-1].strftime("%d.%m") not in homeworks else week) else 1,
            )
            if upd:
                await call.answer(Texts.UPDATED)

        case "mark":
            if await get_mark_info(call, bot=bot, mark_id=match.group(2)):
                await call.answer(Texts.UPDATED)

        case "lesson":
            if await get_lesson_info(call, bot=bot, lesson_id=match.group(2).split("/")[0], lesson_type=match.group(2).split("/")[1]):
                await call.answer(Texts.UPDATED)


class Mark(BaseModel):
    value: int
    weight: int


class CalculatorWeightedAverageMarks:
    calcs: dict[str, tuple["CalculatorWeightedAverageMarks", float]] = {}

    def __init__(self, marks: typing.Optional[list[Mark]] = None):
        self.marks = marks or []

    def add_mark(self, value: int, weight: int):
        self.marks.append(Mark(value=value, weight=weight))

        return self.calculate()

    def calculate(self):
        return sum([mark.value * mark.weight for mark in self.marks]) / sum([mark.weight for mark in self.marks]) if self.marks else 0


@router.message(Command("calc", "calculate", "calculator"))
@router.chosen_inline_result(
    F.result_id == Texts.Inline.CALCULATOR.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(F.data == Texts.Inline.CALCULATOR.id)
async def calculator_cmd(update: types.Message | types.ChosenInlineResult | types.CallbackQuery, bot: Bot):
    user = database.user(update.from_user.id)
    if not user.token:
        _id = uuid.uuid4().hex
        calc = CalculatorWeightedAverageMarks([])
        CalculatorWeightedAverageMarks.calcs[_id] = (calc, time.time() + 60*60*5)

        await bot.inline.answer(update, Texts.Calculator.ADD_MARKS(
            AVERAGE=0,
            ALL="-"
        ), reply_markup=CALC_MARKS(_id))

        return

    user_data = UserData(user, user.apis)
    try:
        marks_by_subject: SubjectsMarks = await user_data.get(DataType.MARKS_BY_SUBJECT)
    except: # noqa
        marks_by_subject: SubjectsMarks = await user_data.get_cached(DataType.MARKS_BY_SUBJECT)
        cache = True

    _id = uuid.uuid4().hex
    subs = {
        sub.subject_id: sub.subject_name
        for sub in marks_by_subject.payload
    }
    calc = CalculatorWeightedAverageMarks([])
    calc.subs = {
        sub.subject_id: sub.periods
        for sub in marks_by_subject.payload
    }
    CalculatorWeightedAverageMarks.calcs[_id] = (calc, time.time() + 60*60*5)

    await bot.inline.answer(
        update,
        Texts.Calculator.CHOOSE_SUBJECT,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=Texts.Buttons.NULL_LIST,
                        callback_data=f"calc:{_id}:subject:null"
                    )
                ]
            ] + chunks(
                [
                    types.InlineKeyboardButton(
                        text=sname,
                        callback_data=f"calc:{_id}:subject:{sid}"
                    )
                    for sid, sname in subs.items()
                ], 2
            )
        )
    )


@router.callback_query(F.data.regexp(r"calc:(.*):(.*):(.*)").as_("match"))
async def calculator_action(call: types.CallbackQuery, match: re.Match, bot: Bot):
    user = database.user(call.from_user.id)

    _id = match.group(1)
    if _id not in CalculatorWeightedAverageMarks.calcs:
        await call.answer(
            text=Texts.CALLBACK_DEADLINED,
            show_alert=True
        )
        return

    calc = CalculatorWeightedAverageMarks.calcs[_id][0]

    match match.group(2):
        case "subject":
            if match.group(3) == "null":
                calc.marks = []
                await call.answer("OK!")

                await bot.inline.answer(
                    call,
                    Texts.Calculator.ADD_MARKS(
                        AVERAGE=0,
                        ALL="-"
                    ),
                    reply_markup=CALC_MARKS(_id)
                )

                return

            calc.periods = calc.subs[int(match.group(3))]
            await bot.inline.answer(
                call,
                Texts.Calculator.CHOOSE_PERIOD,
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text=p.title,
                                callback_data=f"calc:{_id}:period:{p.start_iso}"
                            )
                        ]
                        for p in calc.periods
                    ]
                )
            )
            await call.answer("OK!")
            return
        case "period":
            calc.marks = [
                Mark(value=int(mark.value), weight=mark.weight)
                for p in calc.periods
                for mark in p.marks
                if p.start_iso == match.group(3)
            ]
            await call.answer("OK!")
        case "add":
            mark = list(map(int, match.group(3).split("-")))

            calc.add_mark(mark[0], mark[1])
            await call.answer("OK!")
        case "remove":
            if not calc.marks:
                return await call.answer()

            calc.marks.remove(calc.marks[-1])
            await call.answer("OK!")
        case "clear":
            if not calc.marks:
                return await call.answer()

            calc.marks = []

            await bot.inline.answer(
                call,
                Texts.Calculator.ADD_MARKS(
                    AVERAGE=0,
                    ALL="-"
                ),
                reply_markup=CALC_MARKS(_id)
            )

            await call.answer("OK!")
            return

    await bot.inline.answer(call, Texts.Calculator.ADD_MARKS(
        AVERAGE=calc.calculate(),
        ALL=user.get("settings", {}).get("marks_sep", " • ").join(
            [
                fmark(value=str(mark.value), weight=mark.weight)
                for mark in calc.marks
            ]
        )
    ), reply_markup=CALC_MARKS(_id))

    now = time.time()
    for k in list(CalculatorWeightedAverageMarks.calcs.keys()):
        if CalculatorWeightedAverageMarks.calcs[k][1] < now:
            del CalculatorWeightedAverageMarks.calcs[k]


@router.message(Command("mark", magic=F.args.regexp(r"([0-9]+)?")))
async def get_mark_info(
    update: types.Message | types.CallbackQuery,
    command: CommandObject = None,
    bot: Bot = None,
    mark_id: typing.Optional[str] = None,
):
    """Get mark information"""

    response = await bot.inline.answer(update, Texts.LOADING)
    user = database.user(update.from_user.id)
    data = UserData(user, user.apis)

    try:
        mark_data: MarkInfo = await data.get(DataType.MARK, mark_id=mark_id if mark_id else int(command.args.strip()))
    except Exception:
        await bot.inline.answer(response, Texts.MARK_NOT_FOUND)
        return False

    await bot.inline.answer(
        response,
        response=Texts.Diary.MARK_INFO(
            random.choice(Texts.Diary.EMOJIS),
            mark=mark_data,
            MARK=fmark(mark_data.value, mark_data.weight),
            IS_EXAM_EMOJI="❗️" if mark_data.is_exam else "",
            CREATED_AT=mark_data.created_at.strftime("%Y-%m-%d %H:%M"),
            COMMENT=(
                escape_html(mark_data.comment or "")
            ) or "❌",
            TOTAL_STUDENTS_COUNT=pluralization_string(
                mark_data.class_results.total_students,
                ["ученик", "ученика", "учеников"]
            ),
            STATS="\n".join([
                (
                    f"<b>{mark_stat.mark_value.five}</b> "
                    f"{'▓'*round(mark_stat.percentage_of_students/10)}"
                    f"{'▒'*(10-round(mark_stat.percentage_of_students/10))}"
                    f" <b>({mark_stat.percentage_of_students}%, {mark_stat.number_of_students} уч.)</b>"
                )
                for mark_stat in mark_data.class_results.marks_distributions
            ])
        ),
        reply_markup=[
            [
                {
                    "text": Texts.Buttons.LESSON_INFO,
                    "url": start_with_args(f"lesson_{mark_data.activity.schedule_item_id}_PLAN")
                }
            ],
            [
                {
                    "text": Texts.Buttons.UPDATE,
                    "callback_data": f"diary:mark:{mark_data.id}:upd",
                }
            ]
        ]
    )

    return True


@router.message(Command("lesson", magic=F.args.regexp(r"([0-9]+)?")))
async def get_lesson_info(
    update: types.Message | types.CallbackQuery,
    command: CommandObject = None,
    bot: Bot = None,
    lesson_id: typing.Optional[str] = None,
    lesson_type: str = "PLAN",
):
    """Get lesson information"""

    response = await bot.inline.answer(update, Texts.LOADING)
    user = database.user(update.from_user.id)
    data = UserData(user, user.apis)

    try:
        lesson_data: LessonScheduleItem = await data.get(
            DataType.SCHEDULE_ITEM,
            lesson_id=lesson_id if lesson_id else int(command.args.strip()),
            lesson_type=lesson_type
        )
    except Exception:
        await bot.inline.answer(response, Texts.LESSON_NOT_FOUND)
        return False

    await bot.inline.answer(
        response,
        response=Texts.Diary.LESSON_INFO(
            random.choice(Texts.Diary.EMOJIS),
            lesson=lesson_data,
            topic=lesson_data.details.lesson_topic or "❌",
            THEMES=(
                Texts.Diary.Lesson.THEMES(
                    "\n".join([
                        f"• <i>«{theme.title}»</i>"
                        for theme in lesson_data.details.theme.theme_frames
                        if theme.title and lesson_data.details.theme and lesson_data.details.theme.theme_frames
                    ])
                ) if lesson_data.details and lesson_data.details.theme and lesson_data.details.theme.theme_frames else ""
            ),
            MARKS=(
                Texts.Diary.Lesson.MARKS(
                    "\n".join([
                        Texts.Diary.Lesson.MARK(
                            MARK_URL=start_with_args("mark_" + str(mark.id)),
                            MARK=fmark(mark.value, mark.weight),
                            CONTROL_FORM_NAME=mark.control_form_name,
                            IS_EXAM_EMOJI="❗️" if mark.is_exam else "",
                            MODE="выставления" if mark.updated_at == mark.created_at else "изменения",
                            UPDATED_AT=mark.updated_at.strftime("%d.%m.%Y %H:%M"),
                            COMMENT=(
                                escape_html(mark.comment or "")
                            ) or "❌"
                        )
                        for mark in lesson_data.marks
                    ])
                ) if lesson_data.marks else ""
            ),
            HOMEWORKS=(
                Texts.Diary.Lesson.HOMEWORKS(
                    "\n".join([
                        f"• <i>{homework.homework}</i>"
                        for homework in lesson_data.lesson_homeworks
                    ])
                ) if lesson_data.lesson_homeworks else ""
            )
        ),
        reply_markup=[
            [
                {
                    "text": Texts.Buttons.UPDATE,
                    "callback_data": f"diary:lesson:{lesson_data.id}/{lesson_data.lesson_type}:upd",
                }
            ]
        ]
    )

    return True
