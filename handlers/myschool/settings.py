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
from handlers.myschool.router import APIs, MySchool, MySchoolUser, router
from utils.other import handler
from utils.texts import Texts

TEXT = Texts.MySchool.SETTINGS
NOTIFICATIONS = Texts.MySchool.SETTINGS_NOTIFICATIONS


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
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("settings")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Настройки",
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def settings(update: Message | CallbackQuery, apis: APIs, user: User):
    """Настройки"""

    return await update.bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis)
    )


@handler()
async def goals(update: CallbackQuery, apis: APIs, user: User):
    settings = user.db_settings
    settings["goals"] = not settings.get("goals", False)
    user.db_settings = settings
    await update.bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis)
    )


@handler()
async def notifications(update: CallbackQuery, apis: APIs, user: User, attr: Optional[str] = None):
    if attr:
        settings = user.db_settings
        settings["notifications"] = settings.get("notifications", {})
        settings["notifications"][attr] = not settings["notifications"].get(attr, False)
        user.db_settings = settings

    await update.bot.inline.answer(
        update=update,
        response=NOTIFICATIONS,
        reply_markup=markup(user, apis, "notifications")
    )
