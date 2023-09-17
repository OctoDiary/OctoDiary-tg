from .router import router, MySchool, MySchoolUser, APIs
from aiogram.types import Message, CallbackQuery, InlineQuery, ChosenInlineResult
from aiogram import F, Bot
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import User, Database

@router.inline_query(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text.strip() == ""
)
async def inline_query(update: InlineQuery, bot: Bot, user: User, apis: APIs):
    pass
    # await update.answer(
    #     results=[
            
    #     ]
    # )

