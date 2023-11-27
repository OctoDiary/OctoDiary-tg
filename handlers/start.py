#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.types import Message

from database import Database
from utils.keyboard import ABOUT, DEFAULT, DEFAULT_MES
from utils.other import get_hash
from utils.texts import Texts

router = Router(name="Start")


@router.message(CommandStart())
async def start(message: Message):
    user = Database().user(message.from_user.id)
    await message.answer(
        text=(
            Texts.START(USER_FULL_NAME=message.from_user.full_name)
        ) + (
            Texts.START_GO_AUTH
            if not user.token
            else ""
        ),
        reply_markup=(
            (
                DEFAULT
                if user.system == Texts.Systems.MY_SCHOOL
                else DEFAULT_MES
            )
            if message.chat.type == ChatType.PRIVATE
            and user.token
            else None
        )
    )


@router.message(F.text == Texts.Buttons.PROJECT_ABOUT)
async def about(message: Message):
    await message.answer(
        text=Texts.ABOUT_PROJECT(HASH=get_hash()),
        reply_markup=ABOUT,
        disable_web_page_preview=True
    )
