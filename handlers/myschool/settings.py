from .router import router, MySchool, APIs, MySchoolUser
from aiogram.types import Message, CallbackQuery, InlineQuery, ChosenInlineResult
from aiogram import F, Bot
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import User


TEXT = """
⚙️ <b>Настройки</b>

• <b>Цели</b> - покажут, сколько осталось оценок до желаемого среднего балла
• <b>Уведомления</b> - включить / отключить уведомления определенных событий

"""
NOTIFICATIONS = """
⚙️ <b>Настройки</b> [<code>Уведомления</code>]

• <b>Оценки</b> - уведомления о новых оценках (или об изменении какой-либо оценки)
"""


def markup(user: User, apis: APIs, section: str = None):
    return [
        [
            {
                "text": "Цели > " + ("✅" if user.db_settings.get("goals", False) else "❌"),
                "callback": goals,
                "kwargs": {"apis": apis, "user": user}
            },
            {
                "text": "Уведомления",
                "callback": notifications,
                "kwargs": {"apis": apis, "user": user}
            },
        ]
    ] if not section else [
        [
            {
                "text": "Оценки > " + ("✅" if user.db_settings.get("notifications", {}).get("create_mark", False) else "❌"),
                "callback": notifications,
                "kwargs": {"apis": apis, "user": user, "attr": "create_mark"}
            },
            {
                "text": "Назад",
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
async def settings(update: Message | CallbackQuery, apis: APIs, user: User):
    """Настройки"""

    return await update.bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis)
    )


async def goals(update: CallbackQuery, apis: APIs, user: User):
    settings = user.db_settings
    settings["goals"] = not settings.get("goals", False)
    user.db_settings = settings
    await update.bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis)
    )


async def notifications(update: CallbackQuery, apis: APIs, user: User, attr: str = None):
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


