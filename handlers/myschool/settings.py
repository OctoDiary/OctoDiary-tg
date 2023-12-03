#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import os
from typing import Optional

import segno
from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from database import User
from handlers.myschool.router import APIs, MySchool, MySchoolUser, isMySchoolUser, router
from utils.other import handler
from utils.texts import Texts

TEXT = Texts.SETTINGS
NOTIFICATIONS = Texts.SETTINGS_NOTIFICATIONS


def markup(user: User, apis: APIs, section: Optional[str] = None):
    return [
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
                "text": Texts.Buttons.APP_AUTHORIZATION,
                "callback": send_app_auth,
                "kwargs": {"user": user}
            }
        ]
    ] if not section else [
        [
            {
                "text": Texts.Buttons.MARKS + (
                    "✅" if user.db_settings.get("notifications", {}).get("create_mark", False) else "❌"),
                "callback": notifications,
                "kwargs": {"apis": apis, "user": user, "attr": "create_mark"}
            },
            {
                "text": Texts.Buttons.BACK,
                "callback": settings,
                "kwargs": {"apis": apis, "user": user}
            }
        ]
    ] if section == "notifications" else None


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("settings")
)
@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Настройки",
    F.chat.type == ChatType.PRIVATE
)
@handler()
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

    qr_code = segno.make_qr(
        content="dnevnik-mes://tgbot?code=%s&system=1" % user.token,

    )
    qr_code.save(f"app_auth_qr_code_{user.id}.png", scale=5)

    await update.bot.send_photo(
        update.from_user.id,
        photo=FSInputFile(f"app_auth_qr_code_{user.id}.png"),
        caption=Texts.SETTINGS_APP_AUTH,
        reply_markup=update.bot.inline.generate_markup([
            [
                {
                    "text": Texts.SETTINGS_APP_AUTH_DIRECTLY,
                    "url": "https://octodiary.dsop.online/redir?token=%s&system=1" % user.token
                }
            ]
        ])
    )

    os.remove(f"app_auth_qr_code_{user.id}.png")
