#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database import Database, User
from handlers.myschool.router import APIs, MySchool, MySchoolUser, isMySchoolUser, router
from octodiary.exceptions import APIError
from octodiary.types.myschool.mobile.family_profile import Child, FamilyProfile
from utils.other import handler
from utils.texts import Texts


def child_profile_info(child: Child) -> str:
    return Texts.MySchool.CHILD_INFO(
        child=child
    )


def profile_info(profile: FamilyProfile, from_db: str) -> str:
    text = Texts.MySchool.PROFILE_INFO(
        from_db=from_db,
        profile=profile,
        PROFILE_TYPE='Родитель' if profile.profile.type == 'parent' else 'Ученик',
        PHONE=profile.profile.phone or "Нет информации",
        BIRTH_DATE=profile.profile.birth_date or "Нет информации",
        EMAIL=profile.profile.email or "Нет информации",
    )

    if profile.profile.type == "parent":
        text += Texts.PROFILE_INFO_CHILDREN
        text += "\n".join([child_profile_info(child) for child in profile.children])

    text += Texts.PROFILE_INFO_LOGOUT
    return text


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("profile")
)
@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == Texts.Buttons.PROFILE,
    F.chat.type == ChatType.PRIVATE
)
@handler()
async def profile_cmd(update: Message | CallbackQuery, apis: APIs, user: User, *, is_inline: bool = False):
    """Get profile"""

    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    from_db = ""
    try:
        profile = await apis.mobile.get_profile(user.db_profile_id)
    except APIError:
        profile = FamilyProfile.model_validate(user.db_profile)
        from_db = Texts.FROM_DB

    await update.bot.inline.answer(
        response,
        response=profile_info(profile, from_db),
        reply_markup={
            "text": Texts.Buttons.UPDATE,
            "callback": profile_cmd,
            "kwargs": {
                "apis": apis,
                "user": user,
                "is_inline": is_inline
            },
            "reusable": True,
            "disable_deadline": True
        }
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)


@router.message(
    F.func(isMySchoolUser),
    F.func(MySchoolUser).as_("user"),
    Command("logout")
)
@handler()
async def logout_command(message: Message, user: User):
    """Logout"""
    await message.bot.inline.answer(
        update=message,
        response=Texts.LOGOUT_CONFIRM,
        reply_markup=[
            {
                "text": "✅",
                "callback": logout,
                "kwargs": {
                    "user": user
                }
            },
            {
                "text": "❌",
                "callback": cancel
            }
        ]
    )


@handler()
async def logout(call: CallbackQuery, user: User):
    if call.from_user.id != int(user.id):
        await call.answer(Texts.NOT_FOR_YOU, show_alert=True)
        return

    await call.answer(Texts.EXITING)
    await call.message.delete()
    await call.message.answer(Texts.YOU_ARE_LOGGED_OUT, reply_markup=ReplyKeyboardRemove())
    Database().pop(str(call.from_user.id))


@handler()
async def cancel(call: CallbackQuery):
    await call.message.delete()
