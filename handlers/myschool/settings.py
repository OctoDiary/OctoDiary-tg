#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from typing import Optional

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

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
        ]
    ] if not section else [
        [
            {
                "text": Texts.Buttons.MARKS + ("✅" if user.db_settings.get("notifications", {}).get("create_mark", False) else "❌"),
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
        reply_markup=markup(user, apis)
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
