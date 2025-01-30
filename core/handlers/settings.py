#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import os
import random
import re
import secrets
from typing import Optional

import requests
import segno
from aiogram import Router, F, types, Bot, enums
from aiogram.filters import Command

from core.misc.texts import Texts
from core.misc.utils import fmark, get_date, get_week_for_date, MONTH_NAME_NUMERALS, run_sync
from core.services.api import UserData
from core.services.database import database, User

router = Router(name="Settings")


def get_section(name: str | list[str], expandable: bool = False):
    if isinstance(name, list):
        return "<b>" + " | ".join([
            getattr(Texts.Settings.SectionsNames, n, "Упс-с... Ты не должен это видеть, разраб где-то наложал :)\n")
            for n in name
        ]) + f"</b>\n<blockquote{' expandable' if expandable else ''}>{getattr(Texts.Settings.SectionsInfo, name[0], "Упс-с... Ты не должен это видеть, разраб где-то наложал :)")}</blockquote>"

    return (
        "<b>" + getattr(Texts.Settings.SectionsNames, name, "Упс-с... Ты не должен это видеть, разраб где-то наложал :)\n") + "</b>"
        + f"\n<blockquote{' expandable' if expandable else ''}>{getattr(Texts.Settings.SectionsInfo, name, 'Упс-с... Ты не должен это видеть, разраб где-то наложал :)')}</blockquote>"
    )


SettingsScheme = {
    "diary": (
        lambda _: Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS)).without_html,
        lambda user: (
            Texts.Settings.BASE
            + Texts.Settings.SECTION(Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS)).without_html)
            + "\n\n" + (
                "\n\n".join([
                    get_section(["schedule", "homeworks", "marks"]),
                    get_section("weeks_offset"),
                    get_section("marks_separator"),
                    get_section("week_format")
                ])
            )
        ),
        {
            "schedule": (
                lambda _: Texts.Diary.Commands.diary__schedule,
                lambda user: (
                    Texts.Settings.BASE
                    + Texts.Settings.SECTION(Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS)).without_html)
                    + Texts.Settings.SECTION(Texts.Diary.Commands.diary__schedule)
                    + "\n\n" + (
                        "\n\n".join([
                            get_section("schedule_new_format"),
                            get_section("schedule_show_custom_events"),
                            get_section("schedule_show_other_events"),
                            get_section("schedule_details")
                        ])
                    )
                ),
                {
                    "format": (
                        lambda user: (
                                f"[{'✅' if user.db_settings.get('schedule_new_format', True) else '❎'}] "
                                + Texts.Settings.Buttons.SCHEDULE_NEW_FORMAT
                        ),
                        None,
                        ("schedule_new_format", "not,True")
                    ),
                    "show_custom_events": (
                        lambda user: (
                                f"[{'✅' if user.db_settings.get('schedule_show_custom_events', False) else '❎'}] "
                                + Texts.Settings.Buttons.SHOW_CUSTOM_EVENTS
                        ),
                        None,
                        ("schedule_show_custom_events", "not")
                    ),
                    "show_other_events": (
                        lambda user: (
                                f"[{'✅' if user.db_settings.get('schedule_show_other_events', True) else '❎'}] "
                                + Texts.Settings.Buttons.SHOW_OTHER_EVENTS
                        ),
                        None,
                        ("schedule_show_other_events", "not,True")
                    ),
                    "items": (
                        lambda user: Texts.Settings.Buttons.SCHEDULE_DETAILS,
                        lambda user: "😶‍🌫️ Здесь пока пусто",
                        {
                            str(i): (
                                lambda user, I=i, NAME=name: f"[{'✅' if I in user.db_settings.get('sch_items', ["type", "marks", "homeworks", "room"]) else '❎'}] " + NAME,
                                None,
                                ("sch_items", "l-" + str(i))
                            )
                            for i, name in Texts.Diary.Schedule.Items.items()
                        }
                    )
                }, 0
            ),
            "homeworks": (
                lambda _: Texts.Diary.Commands.diary__homeworks,
                lambda user: (
                    Texts.Settings.BASE
                    + Texts.Settings.SECTION(Texts.Diary.BASE(random.choice(Texts.Diary.EMOJIS)).without_html)
                    + Texts.Settings.SECTION(Texts.Diary.Commands.diary__homeworks)
                    + "\n\n" + (
                        "\n\n".join([
                            get_section("tests_buttons"),
                            get_section("tests_in_web_app")
                        ])
                    )
                ),
                {
                    "show_tests_buttons": (
                        lambda user: (
                            f"[{'✅' if user.db_settings.get('tests_buttons', False) else '❎'}] "
                            + Texts.Settings.Buttons.SHOW_TESTS_BUTTONS
                        ),
                        None,
                        ("tests_buttons", "not")
                    ),
                    "tests_in_web_app": (
                        lambda user: (
                                f"[{'✅' if user.db_settings.get('tests_in_web_app', False) else '❎'}] "
                                + Texts.Settings.Buttons.TESTS_IN_WEB_APP
                        ) if user.db_settings.get('tests_buttons', False) else None,
                        None,
                        ("tests_in_web_app", "not")
                    )
                }, 0
            ),
            "marks_by_date": (
                lambda _: Texts.Diary.Commands.diary__marks_by_date,
                lambda user: "😶‍🌫️ Здесь пока пусто",
                {}, 1
            ),
            "marks_by_subject": (
                lambda _: Texts.Diary.Commands.diary__marks_by_subject,
                lambda user: "😶‍🌫️ Здесь пока пусто",
                {
                    "goals": (
                        lambda user: (
                            f"[{'✅' if user.db_settings.get('goals', False) else '❎'}] "
                            + Texts.Settings.Buttons.GOALS
                        ),
                        None,
                        ("goals", "not")
                    ),
                }, 1
            ),
            "weeks_offset": (
                lambda _: Texts.Settings.Buttons.WEEKS_OFFSET,
                lambda user: "😶‍🌫️ Здесь пока пусто",
                {
                    str(i): (
                        lambda user, I=i: str(I) + (" ✅" if user.db_settings.get("weeks_offset", 2) == I else ""),
                        None,
                        ("weeks_offset", i)
                    )
                    for i in range(1, 6)
                }
            ),
            "marks_sep": (
                lambda _: Texts.Settings.Buttons.MARKS_SEPARATOR,
                lambda user: "😶‍🌫️ Здесь пока пусто",
                {
                    str(i): (
                        lambda user, I=i: I.join([fmark("5", 2), fmark("4", 1), fmark("5", 3)]) + (" ✅" if user.db_settings.get("marks_sep", " • ") == I else ""),
                        None,
                        ("marks_sep", i)
                    )
                    for i in [" • ", " | ", "; ", " - ", " : ", " / ", " — "]
                }
            ),
            "week_format": (
                lambda _: Texts.Settings.Buttons.WEEK_FORMAT,
                lambda user: "😶‍🌫️ Здесь пока пусто",
                {
                    "short": (
                        lambda user: (
                             (
                                f"{week[0].strftime('%d.%m')} — {week[-1].strftime('%d.%m')}"
                                if week[0].year == week[-1].year
                                else f"{week[0].strftime('%d.%m.%Y')} — {week[-1].strftime('%d.%m.%Y')}"
                             ) if (week := get_week_for_date(get_date())) else ""
                        ) + (" ✅" if user.db_settings.get("week_format", "short") == "short" else ""),
                        None,
                        ("week_format", "short")
                    ),
                    "full": (
                        lambda user: (
                             (
                                 (
                                     f"{week[0].day} {MONTH_NAME_NUMERALS[week[0].month].lower()}"
                                     f" — {week[-1].day} {MONTH_NAME_NUMERALS[week[-1].month].lower()}"
                                 ) if week[0].year == week[-1].year else (
                                     f"{week[0].day} {MONTH_NAME_NUMERALS[week[0].month].lower()} {week[0].year}"
                                     f" — {week[-1].day} {MONTH_NAME_NUMERALS[week[-1].month].lower()} {week[-1].year}"
                                 )
                             ) if (week := get_week_for_date(get_date())) else ""
                        ) + (" ✅" if user.db_settings.get("week_format", "short") == "full" else ""),
                        None,
                        ("week_format", "full")
                    )
                }
            )
        }, 0
    ),
    "notifications": (
        lambda _: Texts.Settings.Buttons.NOTIFICATIONS,
        lambda user: "😶‍🌫️ Здесь пока пусто",
        {}, 0
    ),
    "app_auth": (
        lambda _: Texts.Settings.Buttons.APP_AUTHORIZATION,
        lambda _: "",
        {}
    ),
    "refresh_token": (
        lambda _: Texts.Settings.Buttons.REFRESH_TOKEN,
        lambda _: "",
        {}
    )
}


def get_markup(
    user: User,
    section: Optional[str] = None
):
    mdata: dict = SettingsScheme
    if section:
        if "@" in section:
            for i in section.split("@"):
                mdata = mdata[i][2]
        else:
            mdata = mdata[section][2]

    return [
        [
            {
                "text": text,
                "callback_data": (
                    "settings:"
                    + (section or "")
                    + (
                        f"{'@' if section else ''}{section_name}"
                        if isinstance(data[2], dict)
                        else f"/{data[2][0]}={data[2][1]}"
                    )
                )
            }
            for section_name, data in mdata.items()
            if (text := data[0](user))
            and len(data) == 4
            and data[3] == i
        ]
        for i in range(10)
    ] + [
        [
            {
                "text": text,
                "callback_data": (
                    "settings:"
                    + (section or "")
                    + (
                        f"{'@' if section else ''}{section_name}"
                        if isinstance(data[2], dict)
                        else f"/{data[2][0]}={data[2][1]}"
                    )
                )
            }
        ]
        for section_name, data in mdata.items()
        if (text := data[0](user))
        and len(data) == 3
    ] + (
        [
            [
                {
                    "text": Texts.Settings.Buttons.BACK,
                    "callback_data": "settings:" + (
                        section.removesuffix("@" + section.split("@")[-1]) if section and "@" in section else ""
                    )
                }
            ]
        ] if section else [
            [
                {
                    "text": Texts.Buttons.SUPPORT_CHAT,
                    "url": "https://t.me/OctoDiaryChat"
                }
            ]
        ]
    )


def get_text(user: User, section: Optional[str] = None):
    text: str
    section_data: dict = SettingsScheme
    if section:
        if "@" in section:
            for i in section.split("@")[:-1]:
                section_data = section_data[i][2]

            text = section_data[section.split("@")[-1]][1](user)
        else:
            text = section_data[section][1](user)
    else:
        text = Texts.Settings.ROOT(random.choice(Texts.Diary.EMOJIS))

    return text


@router.message(Command("settings"), F.chat.type == enums.ChatType.PRIVATE)
@router.message(F.text == Texts.Buttons.SETTINGS, F.chat.type == enums.ChatType.PRIVATE)
async def settings_cmd(update: types.Message, bot: Bot):
    user = database.user(update.from_user.id)
    if not user.token:
        return await update.answer(
            Texts.NOT_AUTHORIZED
        )

    await bot.inline.answer(
        update=update,
        response=get_text(user),
        reply_markup=get_markup(user)
    )


@router.callback_query(F.data.regexp(r"settings:(.*)").as_("match"))
async def settings_callback(call: types.CallbackQuery, bot: Bot, match: re.Match):
    user = database.user(call.from_user.id)
    if not user.token:
        return await call.answer(
            Texts.NOT_AUTHORIZED.without_html
        )

    match match.group(1):
        case "diary" | "homeworks" | "notifications" | "schedule" | "marks_by_subject" | "marks_by_date" | "":
            await bot.inline.answer(
                update=call,
                response=get_text(user, match.group(1)),
                reply_markup=get_markup(user, match.group(1))
            )

            return await call.answer()
        case "app_auth":
            await call.answer(Texts.WAIT)
            info = {
                "token": user.token,
                "system": 0 if user.system == Texts.Systems.MES else 1,
                "timeout": 60 * 5
            }
            key = secrets.token_hex(16)
            await run_sync(
                requests.post,
                f"https://octodiary.den4iksop.org/api/app_auth/{key}",
                json=info,
            )
            qr_code = segno.make_qr(content=f"https://octodiary.den4iksop.org/redir?token={key}")
            qr_code.save(f"files/app_auth_qr_code_{user.id}.png", scale=5, kind="png")

            await bot.send_photo(
                call.from_user.id,
                photo=types.FSInputFile(f"files/app_auth_qr_code_{user.id}.png"),
                caption=Texts.Settings.APP_AUTH,
                reply_markup=bot.inline.generate_markup({
                    "text": Texts.Settings.Buttons.APP_AUTH_DIRECTLY,
                    "url": f"https://octodiary.den4iksop.org/redir?token={key}"
                }),
                has_spoiler=True
            )

            os.remove(f"files/app_auth_qr_code_{user.id}.png")
            return
        case "refresh_token":
            user.token = await UserData.refresh_token(token=user.token)
            await call.answer(Texts.TOKEN_REFRESHED, show_alert=True)
            return
        case X if (match2 := re.match(r"(.*)/(.*)=(.*)", X)):
            match match2.group(3):
                case "not":
                    user.db_settings = user.db_settings | {
                        match2.group(2): not user.db_settings.get(match2.group(2), False)
                    }
                case "not,True":
                    user.db_settings = user.db_settings | {
                        match2.group(2): not user.db_settings.get(match2.group(2), True)
                    }
                case x if (match3 := re.match(r"l-(.*)", x)):
                    if match3.group(1) in (items := user.db_settings.get(match2.group(2), ["type", "marks", "homeworks", "room"])):
                        items.remove(match3.group(1))
                        user.db_settings = user.db_settings | {
                            match2.group(2): items
                        }
                    else:
                        user.db_settings = user.db_settings | {
                            match2.group(2): items + [match3.group(1)]
                        }
                case value:
                    user.db_settings = user.db_settings | {
                        match2.group(2): int(value) if value.isdigit() else {"true": True, "false": False}.get(value, value)
                    }

            await bot.inline.answer(
                update=call,
                response=get_text(user, match2.group(1)),
                reply_markup=get_markup(user, match2.group(1))
            )

            return await call.answer(Texts.SUCCESSFULLY)
        case X if "@" in X:
            await bot.inline.answer(
                update=call,
                response=get_text(user, X),
                reply_markup=get_markup(user, X)
            )

            return await call.answer()
        # case _:
        #
        #     if m2 := re.match(r"(.*):(.*):s-(.*)", match.group(1)):
        #         ...
        #     elif m2 := re.match(r"(.*):(.*)", match.group(1)):
        #         ...

    await call.answer("What? Who? What you doing?", show_alert=True)
