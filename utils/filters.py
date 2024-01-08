#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import inspect

from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.types import User as AiogramUser

from database import Database, User
from utils.texts import Texts

from apis import MesAPIs, MySchoolAPIs


class AuthFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            await message.answer(text=Texts.Authorization.WRITE_BEHALF_ACCOUNT)
            return False
        if not message.text:
            await message.answer(text=Texts.Authorization.WRITE_TEXT_MESSAGE)
            return False

        return True


def is_authorized(user: AiogramUser):
    return Database().user(user.id).token is not None


def user_apis(user: User):
    return (
        MesAPIs(user.token)
        if user.system == Texts.Systems.MES
        else MySchoolAPIs(user.token)
        if user.system == Texts.Systems.MY_SCHOOL
        else None
    )


def apis_and_user(func):
    def wrapper(*args, **kwargs):
        update = args[0]
        if is_authorized(update.from_user):
            user = Database().user(update.from_user.id)
            return func(*args, **kwargs | {
                "apis": user_apis(user),
                "user": user
            })
        return empty_func()
    wrapper.params = list(inspect.signature(func).parameters.keys())
    return wrapper


async def empty_func(*args, **kwargs):
    """This function is empty"""
