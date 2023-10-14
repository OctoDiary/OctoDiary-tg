#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram import Router
from aiogram.types import CallbackQuery, ChosenInlineResult, InlineQuery, Message

from database import Database, User
from octodiary.asyncApi.mes import AsyncMobileAPI

from utils.texts import Texts

router = Router(name="MesRouter")


class APIs:
    def __init__(self, token: str) -> None:
        self.mobile = AsyncMobileAPI(token)
        self.web = None


def Mes(
    update: Message | CallbackQuery | InlineQuery | ChosenInlineResult
) -> APIs | bool:
    if (
        user.system == Texts.Systems.MES and bool(user.token)
        if update.from_user and (user := Database().user(update.from_user.id))
        else False
    ):
        return APIs(user.token)
    return False

def MesUser(
    update: Message | CallbackQuery | InlineQuery | ChosenInlineResult
) -> User | bool:
    return (
        user
        if update.from_user
        and (user := Database().user(update.from_user.id))
        and user.system == Texts.Systems.MES
        and bool(user.token)
        else False
    )

def isMesUser(update: Message | CallbackQuery | InlineQuery | ChosenInlineResult) -> bool:
    return (
        update.from_user
        and (user := Database().user(update.from_user.id))
        and user.system == Texts.Systems.MES
        and bool(user.token)
    )
