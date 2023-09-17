from aiogram import Router
from aiogram.types import CallbackQuery, ChosenInlineResult, InlineQuery, Message
from database import Database, User
from octodiary.asyncApi.myschool import AsyncMobileAPI, AsyncWebAPI

router = Router(name="MySchoolRouter")


class APIs:
    def __init__(self, token: str) -> None:
        self.mobile = AsyncMobileAPI(token)
        self.web = AsyncWebAPI(token)


def MySchool(
    update: Message | CallbackQuery | InlineQuery | ChosenInlineResult
) -> APIs | bool:
    if (
        user.system == "myschool" and bool(user.token)
        if update.from_user and (user := Database().user(update.from_user.id))
        else False
    ):
        return APIs(user.token)
    return False

def MySchoolUser(
    update: Message | CallbackQuery | InlineQuery | ChosenInlineResult
) -> User | bool:
    return (
        user
        if update.from_user
        and (user := Database().user(update.from_user.id))
        and user.system == "myschool"
        and bool(user.token)
        else False
    )