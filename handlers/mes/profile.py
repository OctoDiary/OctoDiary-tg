#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database import Database, User
from handlers.mes.router import APIs, Mes, MesUser, isMesUser, router
from octodiary.exceptions import APIError
from octodiary.types.mes.mobile.family_profile import Child, FamilyProfile
from utils.other import handler
from utils.texts import Texts


async def child_profile_info(child: Child, apis: APIs, user: User) -> str:
    return (
        Texts.Mes.CHILD_INFO.FIO(child=child)
        + (
            Texts.Mes.CHILD_INFO.PHONE(child=child)
            if child.phone
            else ""
        ) + (
            Texts.Mes.CHILD_INFO.BIRTH_DATE(child=child)
            if child.birth_date
            else ""
        ) + (
            Texts.Mes.CHILD_INFO.BALANCE(BALANCE=str(balance / 100) + " ₽", contract_id=child.contract_id)
            if (
                balance := (
                    await apis.mobile.get_status(
                        user.db_profile_id,
                        child.contract_id
                    )
                ).students[0].balance
            )
            else ""
        ) + (
            Texts.Mes.CHILD_INFO.EMAIL(child=child)
            if child.email
            else ""
        ) + Texts.Mes.CHILD_INFO.SCHOOL(child=child)
    )


async def profile_info(profile: FamilyProfile, from_db: str, apis: APIs, user: User) -> str:
    text = (
        Texts.Mes.PROFILE_INFO.START(
            profile=profile,
            from_db=from_db,
            PROFILE_TYPE=(
                'Родитель'
                if profile.profile.type == 'parent'
                else 'Ученик'
            )
        ) + Texts.Mes.PROFILE_INFO.FIO(profile=profile)
        + (
            Texts.Mes.PROFILE_INFO.PHONE(PHONE=profile.profile.phone)
            if profile.profile.phone
            else ""
        ) + (
            Texts.Mes.PROFILE_INFO.EMAIL(EMAIL=profile.profile.email)
            if profile.profile.email
            else ""
        ) + Texts.Mes.PROFILE_INFO.BIRTH_DATE(BIRTH_DATE=profile.profile.birth_date or "Нет информации")
    )

    if profile.profile.type == "parent":
        text += Texts.PROFILE_INFO_CHILDREN
        text += "\n".join(
            [
                await child_profile_info(child, apis, user)
                for child in profile.children
            ]
        )
    else:
        text += (
            Texts.Mes.CHILD_INFO.BALANCE(balance=str(balance // 100) + " ₽", contract_id=profile.children[0].contract_id).replace("├ ", "┌ ")
            if (
                balance := (
                    await apis.mobile.get_status(
                        user.db_profile_id,
                        profile.children[0].contract_id
                    )
                ).students[0].balance
            )
            else ""
        ) + Texts.Mes.CHILD_INFO.SCHOOL(child=profile.children[0]) + "\n"

    text += Texts.PROFILE_INFO_LOGOUT
    return text


@router.message(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    Command("profile")
)
@router.message(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
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
        profile = await apis.mobile.get_family_profile(user.db_profile_id)
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
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
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
