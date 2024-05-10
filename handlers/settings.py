#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import os
from logging import getLogger
from typing import Optional

import segno
from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from apis import APIs
from database import User
from handlers.router import router
from utils.filters import apis_and_user
from utils.other import handler, refresh_mes_token
from utils.texts import Texts

logger = getLogger(__name__)

TEXT = Texts.SETTINGS
NOTIFICATIONS = Texts.SETTINGS_NOTIFICATIONS


def markup(user: User, apis: APIs, section: Optional[str] = None):
    schedule_settings: dict[str, bool] = user.db_settings.get("schedule_details", {})
    return (
        [
            [
                {
                    "text": Texts.Buttons.SETTINGS_GOALS + ("✅" if user.db_settings.get("goals", False) else "❌"),
                    "callback": goals,
                    "kwargs": {"apis": apis, "user": user}
                },
                {
                    "text": Texts.Buttons.NOTIFICATIONS,
                    "callback": notifications,
                    "kwargs": {"apis": apis, "user": user}
                },
            ],
            [
                {
                    "text": Texts.Buttons.SCHEDULE_DETAILS,
                    "callback": schedule_details,
                    "kwargs": {"apis": apis, "user": user}
                }
            ],
            [
                {
                    "text": Texts.Buttons.APP_AUTHORIZATION,
                    "callback": send_app_auth,
                    "kwargs": {"user": user}
                }
            ],
            [
                {
                    "text": Texts.Buttons.REFRESH_TOKEN,
                    "callback": refresh_token,
                    "kwargs": {"user": user}
                }
            ]
        ] + (
            [
                {
                    "text": Texts.Buttons.CHOOSE_CHILD_PROFILE,
                    "callback": choose_child_profile_menu,
                    "kwargs": {"apis": apis, "user": user}
                }
            ] if user.db_profile["profile"]["type"] == "parent" else []
        ) if not section else (
            [
                [
                    {
                        "text": Texts.Buttons.MARKS + (
                            "✅" if user.db_settings.get("notifications", {}).get("create_mark", False) else "❌"),
                        "callback": notifications,
                        "kwargs": {"apis": apis, "user": user, "attr": "create_mark"}
                    }
                ]

            ] + (
                [
                    [
                        {
                            "text": Texts.Buttons.HIDE_MARK + (
                                "✅" if user.db_settings.get("notifications", {}).get("hide_mark", False) else "❌"
                            ),
                            "callback": notifications,
                            "kwargs": {"apis": apis, "user": user, "attr": "hide_mark"}
                        }
                    ]
                ] if user.db_settings.get("notifications", {}).get("create_mark", False) else []
            ) + [
                [
                    {
                        "text": Texts.Buttons.BACK,
                        "callback": settings,
                        "kwargs": {"apis": apis, "user": user}
                    }
                ]
            ]
        ) if section == "notifications" else (
            [
                [
                    {
                        "text": f"{'👧' if child['sex'] == 'female' else '👦'} {child['first_name']} - {child['class_name']} класс" + (
                            " ✅"
                            if child == user.db_current_child
                            or user.db_profile["children"].index(child) == 0
                            and not user.db_current_child
                            else ""
                        ),
                        "callback": choose_child_profile,
                        "kwargs": {"apis": apis, "user": user, "child": child}
                    }
                ]
                for child in user.db_profile["children"]
            ] + [
                [
                    {
                        "text": Texts.Buttons.BACK,
                        "callback": settings,
                        "kwargs": {"apis": apis, "user": user}
                    }
                ]
            ]
        ) if section == "choose_child_profile" else (
            [
                [
                    {
                        "text": getattr(Texts.ScheduleDetailsSettings, key) + (
                            " > ✅"
                            if schedule_settings.get(key, True)
                            else " > ❌"
                        ),
                        "callback": change_schedule_detail,
                        "kwargs": {"apis": apis, "user": user, "attr": key}
                    }
                ]
                for key in [
                    "show_id",
                    "show_other_lessons",
                    "show_events",
                    "show_theme",
                    "show_homeworks",
                    "show_marks",
                    "show_replaces",
                ]
            ] + [
                [
                    {
                        "text": Texts.Buttons.BACK,
                        "callback": settings,
                        "kwargs": {"apis": apis, "user": user}
                    }
                ]
            ]
        ) if section == "schedule_details" else []
    )


@router.message(Command("settings"))
@router.message(F.text == Texts.Buttons.SETTINGS, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def settings(update: Message | CallbackQuery, apis: APIs, user: User):
    """Settings menu"""

    return await update.bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis),
        disable_web_page_preview=True
    )


@handler()
async def goals(update: CallbackQuery, apis: APIs, user: User):
    await update.answer()
    settings_data = user.db_settings
    settings_data["goals"] = not settings_data.get("goals", False)
    user.db_settings = settings_data
    await update.bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis)
    )


@handler()
async def notifications(update: CallbackQuery, apis: APIs, user: User, attr: Optional[str] = None):
    await update.answer()
    if attr:
        settings_data = user.db_settings
        settings_data["notifications"] = settings_data.get("notifications", {})
        settings_data["notifications"][attr] = not settings_data["notifications"].get(attr, False)
        user.db_settings = settings_data

    await update.bot.inline.answer(
        update=update,
        response=NOTIFICATIONS,
        reply_markup=markup(user, apis, "notifications")
    )


@handler()
async def send_app_auth(update: CallbackQuery, user: User):
    await update.answer()
    if str(update.from_user.id) != user.id:
        return

    qr_code = segno.make_qr(content="dnevnik-mes://tgbot?code=%s&system=1" % user.token)
    qr_code.save(f"app_auth_qr_code_{user.id}.png", scale=5)

    await update.bot.send_photo(
        update.from_user.id,
        photo=FSInputFile(f"app_auth_qr_code_{user.id}.png"),
        caption=Texts.SETTINGS_APP_AUTH,
        reply_markup=update.bot.inline.generate_markup([
            [
                {
                    "text": Texts.SETTINGS_APP_AUTH_DIRECTLY,
                    "url": f"https://octodiary.dsop.online/redir?token=%s&system={0 if user.system == Texts.Systems.MES else 1}" % user.token
                }
            ]
        ])
    )

    os.remove(f"app_auth_qr_code_{user.id}.png")


@handler()
async def choose_child_profile_menu(update: CallbackQuery, apis: APIs, user: User):
    await update.answer()
    if str(update.from_user.id) != user.id:
        return

    await update.bot.inline.answer(
        update=update,
        response=Texts.CHOOSE_CHILD_PROFILE,
        reply_markup=markup(user, apis, "choose_child_profile")
    )


@handler()
async def choose_child_profile(update: CallbackQuery, apis: APIs, user: User, child: dict):
    if str(update.from_user.id) != user.id:
        return

    if child == user.db_current_child:
        return await update.answer("Вы уже выбрали этот профиль")

    user.db_current_child = child

    await update.bot.inline.answer(
        update=update,
        response=Texts.CHOOSE_CHILD_PROFILE,
        reply_markup=markup(user, apis, "choose_child_profile")
    )
    await update.answer()


@handler()
async def refresh_token(update: CallbackQuery, user: User):
    if str(update.from_user.id) != user.id:
        return

    try:
        if user.system == Texts.Systems.MY_SCHOOL:
            user.token = await APIs(
                token=user.token,
                system=user.system
            ).mobile.refresh_token()
        else:
            await refresh_mes_token(user=user)

        await update.answer(Texts.TOKEN_REFRESHED, show_alert=True, cache_time=0)
    except Exception:
        logger.exception("Failed to refresh token for user %s with system %s", str(user.id), user.system)
        await update.answer(Texts.TOKEN_REFRESH_ERROR, show_alert=True, cache_time=0)


@handler()
async def schedule_details(update: CallbackQuery, user: User, apis: APIs):
    if str(update.from_user.id) != user.id:
        return

    await update.bot.inline.answer(
        update=update,
        response=Texts.SCHEDULE_DETAILS,
        reply_markup=markup(user, apis, "schedule_details")
    )


@handler()
async def change_schedule_detail(update: CallbackQuery, user: User, apis: APIs, attr: Optional[str] = None):
    if str(update.from_user.id) != user.id:
        return

    if attr:
        settings_data = user.db_settings
        settings_data["schedule_details"] = settings_data.get("schedule_details", {})
        settings_data["schedule_details"][attr] = not settings_data["schedule_details"].get(attr, True)
        user.db_settings = settings_data

    await update.bot.inline.answer(
        update=update,
        response=Texts.SCHEDULE_DETAILS,
        reply_markup=markup(user, apis, "schedule_details")
    )
