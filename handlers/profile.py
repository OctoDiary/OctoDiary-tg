#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import api
from apis import APIs
from database import Database, User
from handlers.router import router
from octodiary.types.mobile.family_profile import Child, FamilyProfile
from utils.filters import apis_and_user
from utils.other import handler
from utils.texts import Texts


async def child_profile_info(child: Child, apis: APIs, user: User) -> str:
    return (
            Texts.CHILD_INFO.FIO(child=child)
            + (
                Texts.CHILD_INFO.PHONE(child=child)
                if child.phone
                else ""
            ) + (
                Texts.CHILD_INFO.BIRTH_DATE(child=child)
                if child.birth_date
                else ""
            ) + (
                    (
                        Texts.CHILD_INFO.BALANCE(BALANCE=str(balance / 100) + " ₽", contract_id=child.contract_id)
                        if (
                            balance := (
                                await apis.mobile.get_status(
                                    user.db_profile_id,
                                    str(child.contract_id)
                                )
                            ).students[0].balance
                        )
                        else ""
                    )
                    if user.system == Texts.Systems.MES and child.contract_id
                    else ""
            ) + (
                Texts.CHILD_INFO.EMAIL(child=child)
                if child.email
                else ""
            ) + Texts.CHILD_INFO.SCHOOL(child=child)
    )


async def profile_info(profile: api.APIResponse[FamilyProfile], apis: APIs, user: User) -> str:
    text = (
        (Texts.FROM_CACHE(profile.last_cache_time) if profile.is_cache else "")
        + Texts.PROFILE_INFO.START(
            profile=profile.response,
            PROFILE_TYPE=(
                "Родитель"
                if profile.response.profile.type == "parent"
                else "Ученик"
            )
        ) + Texts.PROFILE_INFO.FIO(profile=profile.response)
        + (
            Texts.PROFILE_INFO.PHONE(PHONE=profile.response.profile.phone)
            if profile.response.profile.phone
            else ""
        ) + (
            Texts.PROFILE_INFO.EMAIL(EMAIL=profile.response.profile.email)
            if profile.response.profile.email
            else ""
        ) + Texts.PROFILE_INFO.BIRTH_DATE(BIRTH_DATE=profile.response.profile.birth_date or "Нет информации")
    )

    if profile.response.profile.type == "parent":
        text += Texts.PROFILE_INFO_CHILDREN
        text += "\n".join(
            [
                await child_profile_info(child, apis, user)
                for child in profile.response.children
            ]
        )
    elif user.system == Texts.Systems.MES:
        text += (
            Texts.CHILD_INFO.BALANCE(
                balance=str(balance // 100) + " ₽",
                contract_id=profile.response.children[0].contract_id
            ).replace("├ ", "┌ ")
            if (
                balance := (
                    await apis.mobile.get_status(
                        user.db_profile_id,
                        str(profile.response.children[0].contract_id)
                    )
                ).students[0].balance
            )
            else ""
        ) + Texts.CHILD_INFO.SCHOOL(child=profile.response.children[0]) + "\n"

    text += Texts.PROFILE_INFO_LOGOUT
    return text


@router.message(Command("profile"))
@router.message(F.text == Texts.Buttons.PROFILE, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def profile_cmd(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        *,
        is_inline: bool = False
):
    """Get profile information"""

    response = update if is_inline else await update.bot.inline.answer(update, Texts.LOADING)

    profile = await api.get_profile(user=user, apis=apis)

    await update.bot.inline.answer(
        response,
        response=await profile_info(profile, apis, user),
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


@router.message(Command("logout"))
@handler()
@apis_and_user
async def logout_command(message: Message, user: User, apis: APIs):
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
