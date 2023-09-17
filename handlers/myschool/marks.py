from .router import router, MySchool, APIs, MySchoolUser
from aiogram.types import Message, CallbackQuery, InlineQuery, ChosenInlineResult
from aiogram import F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import User


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("marks")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Оценки",
    F.chat.type == ChatType.PRIVATE
)
async def marks(message: Message, apis: APIs, user: User):
    """Оценки"""

    await message.answer("В разработке...")
