#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import re

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from core.handlers.auth import app_auth, web_auth_result
from core.handlers.diary import calculator_cmd, get_mark_info, get_lesson_info
from core.handlers.feedback import feedback_cmd
from core.keyboards.inline import ABOUT
from core.keyboards.reply import root_menu
from core.misc.texts import Texts
from core.misc.utils import get_hash
from core.services.database import database

router = Router(name="Start")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject, bot: Bot):
    if command.args:
        # from handlers.auth import app_auth, web_auth_beta, Authorization
        # from handlers.schedule import get_lesson_info, get_mark_info

        if command.args == "feedback":
            await feedback_cmd(message, state)
        elif match := re.match(r"app_auth_(.*)", command.args):
            await app_auth(message, state, match, bot)
        elif match := re.match(r"lesson_(.*)_(.*)", command.args):
            await get_lesson_info(message, lesson_id=match.group(1), lesson_type=match.group(2), bot=bot)
        elif match := re.match(r"mark_(.*)", command.args):
            await get_mark_info(message, mark_id=match.group(1), bot=bot)
        elif match := re.match(r"web_auth_(.*)", command.args):
            await web_auth_result(message, state, match, bot)
        elif command.args == "calc":
            await calculator_cmd(message, bot)
        return

    user = database.user(message.from_user.id)
    await message.answer(
        text=(
            Texts.START(USER_FULL_NAME=message.from_user.full_name)
        ) + (
            Texts.START_GO_AUTH
            if not user.token
            else ""
        ),
        reply_markup=(
            root_menu(user.system)
            if message.chat.type == ChatType.PRIVATE and user.token
            else None
        )
    )


@router.message(F.text == Texts.Buttons.PROJECT_ABOUT)
async def about(message: Message):
    user = database.user(message.from_user.id)
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


@router.message(Command("cancel"))
@router.message(F.text == Texts.Buttons.CANCEL)
async def cancel(message: Message, state: FSMContext):
    if not (state_name := await state.get_state()):
        return

    user = database.user(message.from_user.id)

    await state.clear()
    await message.answer(
        text=getattr(Texts, state_name.split(":")[0]).CANCEL,
        reply_markup=root_menu(user.system) if user.token else ReplyKeyboardRemove()
    )
