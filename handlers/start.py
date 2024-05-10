#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import re

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import Database
from handlers.auth import app_auth
from handlers.feedback import feedback_cmd
from handlers.schedule import get_mark_info
from utils.keyboard import ABOUT, DEFAULT, DEFAULT_MES
from utils.other import get_hash
from utils.texts import Texts

router = Router(name="Start")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject):
    if command.args:
        if command.args == "feedback":
            await feedback_cmd(message, state)
        elif match := re.match(r"app_auth_(.*)", command.args):
            await app_auth(message, state, match)
        elif match := re.match(r"lesson_(.*)_(.*)", command.args):
            await get_lesson_info(message, lesson_id=match.group(1), lesson_type=match.group(2))
        elif match := re.match(r"mark_(.*)", command.args):
            await get_mark_info(message, mark_id=match.group(1))
        return

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
    user = Database().user(message.from_user.id)
    await message.answer(
        text=(
            Texts.ABOUT_PROJECT(HASH=get_hash())
            + (
                (
                    Texts.ABOUT_MY_SCHOOL_PROJECT
                    if user.system == Texts.Systems.MY_SCHOOL
                    else Texts.ABOUT_MES_PROJECT
                )
                if user.token
                else (
                        Texts.ABOUT_MES_PROJECT
                        + Texts.ABOUT_MY_SCHOOL_PROJECT
                )
            )
        ),
        reply_markup=ABOUT,
        disable_web_page_preview=True
    )
