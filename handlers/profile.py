#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import api
from apis import MesAPIs, MySchoolAPIs
from database import Database, User
from handlers.router import router
from octodiary.exceptions import APIError
from octodiary.types.mes.mobile.family_profile import Child, FamilyProfile
from utils.filters import apis_and_user
from utils.other import handler
from utils.texts import Texts


async def child_profile_info(child: Child, apis: MesAPIs | MySchoolAPIs, user: User) -> str:
    # if user.system == Texts.Systems.MES:
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
    # else:
    #     return (
    #         Texts.CHILD_INFO(
    #             child=child
    #         )
    #     )


async def profile_info(profile: FamilyProfile, from_db: str, apis: MesAPIs | MySchoolAPIs, user: User) -> str:
    text = (
        Texts.PROFILE_INFO.START(
            profile=profile,
            from_db=from_db,
            PROFILE_TYPE=(
                "Родитель"
                if profile.profile.type == "parent"
                else "Ученик"
            )
        ) + Texts.PROFILE_INFO.FIO(profile=profile)
        + (
            Texts.PROFILE_INFO.PHONE(PHONE=profile.profile.phone)
            if profile.profile.phone
            else ""
        ) + (
            Texts.PROFILE_INFO.EMAIL(EMAIL=profile.profile.email)
            if profile.profile.email
            else ""
        ) + Texts.PROFILE_INFO.BIRTH_DATE(BIRTH_DATE=profile.profile.birth_date or "Нет информации")
    )

    if profile.profile.type == "parent":
        text += Texts.PROFILE_INFO_CHILDREN
        text += "\n".join(
            [
                await child_profile_info(child, apis, user)
                for child in profile.children
            ]
        )
    elif user.system == Texts.Systems.MES:
        text += (
            Texts.CHILD_INFO.BALANCE(
                balance=str(balance // 100) + " ₽",
                contract_id=profile.children[0].contract_id
            ).replace("├ ", "┌ ")
            if (
                balance := (
                    await apis.mobile.get_status(
                        user.db_profile_id,
                        str(profile.children[0].contract_id)
                    )
                ).students[0].balance
            )
            else ""
        ) + Texts.CHILD_INFO.SCHOOL(child=profile.children[0]) + "\n"

    text += Texts.PROFILE_INFO_LOGOUT
    return text


@router.message(Command("profile"))
@router.message(F.text == Texts.Buttons.PROFILE, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def profile_cmd(
        update: Message | CallbackQuery,
        apis: MesAPIs | MySchoolAPIs,
        user: User,
        *,
        is_inline: bool = False
):
    """Get profile information"""

    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    from_db = ""
    try:
        profile = await api.get_profile(user=user, apis=apis)
    except APIError:
        profile = FamilyProfile.model_validate(user.db_profile)
        from_db = Texts.FROM_DB

    await update.bot.inline.answer(
        response,
        response=await profile_info(profile, from_db, apis, user),
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
async def logout_command(message: Message, user: User, apis: MesAPIs | MySchoolAPIs):
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
