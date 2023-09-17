from .router import router, MySchool, APIs, MySchoolUser
from aiogram.types import Message, CallbackQuery, InlineQuery, ChosenInlineResult
from aiogram import F
from aiogram.filters import Command
from aiogram.enums import ChatType
from octodiary.exceptions import APIError
from octodiary.types.myschool.mobile.family_profile import FamilyProfile, Child
from database import User, Database


def child_profile_info(child: Child) -> str:
    return f"""
┌ 👤 <b>{child.last_name} {child.first_name} {child.middle_name}</b>
├ 📞 <code>{child.phone or 'Нет информации'}</code>
├ 📆 <code>{child.birth_date}</code>
└ 📧 <code>{child.email}</code>
"""

def profile_info(profile: FamilyProfile, from_db: str) -> str:
    TEXT = f"""
👤 <b>Профиль</b>
{from_db}<b>{profile.profile.first_name} {profile.profile.last_name}</b> [<b>{'Родитель' if profile.profile.type == 'parent' else 'Ученик'}</b>]

[<b>Личные данные</b> | <b>Контакты</b>]
┌ 👤 <b>{profile.profile.last_name} {profile.profile.first_name} {profile.profile.middle_name}</b>
├ 📞 <code>{profile.profile.phone or 'Нет информации'}</code>
├ 📆 <code>{profile.profile.birth_date or 'Нет информации'}</code>
└ 📧 <code>{profile.profile.email or 'Нет информации'}</code>
"""
    if profile.profile.type == "parent":
        TEXT += "\n[<b>Дети</b> | <b>Личные данные</b>]"
        TEXT += "\n".join([child_profile_info(child) for child in profile.children])
    
    TEXT += "\nℹ️ Чтобы <b>выйти</b>, пропишите команду - /logout"
    return TEXT


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("profile")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Профиль",
    F.chat.type == ChatType.PRIVATE
)
async def profile(update: Message | CallbackQuery, apis: APIs, user: User):
    """Профиль"""

    from_db = ''
    try:
        profile = await apis.mobile.get_profile(user.db_profile_id)
    except APIError:
        profile = FamilyProfile.model_validate(user.db_profile)
        from_db = "<tg-spoiler>❕ Сервер не ответил на запрос, последние загруженные данные:</tg-spoiler>\n"
    
    await update.answer(text=profile_info(profile, from_db))


@router.message(
    F.func(MySchoolUser).as_("user"),
    Command("logout")
)
async def logout_command(message: Message, user: User):
    """Выход"""
    await message.bot.inline.answer(
        update=message,
        response="❗️ Вы действительно хотите <b>выйти</b>?",
        reply_markup=[
            {
                "text": "✅",
                "callback": logout,
                "args": (user,)
            },
            {
                "text": "❌",
                "callback": cancel
            }
        ]
    )


async def logout(call: CallbackQuery, user: User):
    if call.from_user.id != int(user.__id):
        await call.answer("Это не для тебя!", show_alert=True)
        return

    await call.answer("Выход...")
    await call.message.answer("✅ Вы <b>вышли из аккаунта</b>.\n")
    Database().pop(str(call.from_user.id))


async def cancel(call: CallbackQuery):
    await call.message.delete()
    await call.answer("Отмена...")
