#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import Bot, F
from aiogram.types import InlineQuery
from database import User
from utils.other import handler

from .router import APIs, MySchool, MySchoolUser, router


@router.inline_query(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.query.strip() == ""
)
@handler()
async def inline_query(update: InlineQuery, bot: Bot, user: User, apis: APIs):
    pass
