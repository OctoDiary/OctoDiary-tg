#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import requests
from aiogram import F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
)

from apis import APIs
from database import Database, User
from handlers.auth import auth_router
from utils import handler
from utils.filters import apis_and_user
from utils.keyboard import (
    CANCEL,
    DEFAULT,
    DEFAULT_MES,
    YES_OR_NO,
)
from utils.texts import Texts


class WebAuth(StatesGroup):
    code = State()
    confirm = State()


@auth_router.message(Command(commands=["webauth", "weblogin"]))
@handler()
@apis_and_user
async def webauth(message: Message, state: FSMContext, command: CommandObject, apis: APIs, user: User):
    if user.system == Texts.Systems.MES:
        return

    if command.args and command.args.isdigit():
        await state.update_data(code=command.args)
        await state.set_state(WebAuth.confirm)
        await message.reply(Texts.WebAuth.CONFIRM(CODE=command.args), reply_markup=YES_OR_NO)
    else:
        await state.set_state(WebAuth.code)
        await message.reply(Texts.WebAuth.SEND_CODE, reply_markup=CANCEL)


@auth_router.message(WebAuth.code, F.text, F.func(lambda message: message.text.isdigit()))
@handler()
async def webauth_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await state.set_state(WebAuth.confirm)
    await message.reply(Texts.WebAuth.CONFIRM(CODE=message.text), reply_markup=YES_OR_NO)


@auth_router.message(WebAuth.confirm)
@handler()
async def webauth_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data["code"]
    confirm = message.text == Texts.YES
    if not (code and confirm):
        await message.reply(Texts.WebAuth.ERROR)
        await state.clear()
        return

    user = Database().user(str(message.from_user.id))
    reply_markup = (
        DEFAULT if user.system == Texts.Systems.MY_SCHOOL else DEFAULT_MES
    )

    result = requests.post(
        f"https://octodiary.dsop.online/accept_web_auth/{code}",
        json={
            "token": user.token,
            "system": user.system
        },
        timeout=15
    )
    await state.clear()
    if result.json()["status"] == "Success":
        await message.reply(Texts.WebAuth.SUCCESS, reply_markup=reply_markup)
    else:
        await message.reply(Texts.WebAuth.ERROR, reply_markup=reply_markup)
