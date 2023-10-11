#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram.filters import Filter
from aiogram.types import Message

from utils.texts import Texts


class AuthFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            await message.answer(text=Texts.Authorization.WRITE_BEHALF_ACCOUNT)
            return False
        if not message.text:
            await message.answer(text=Texts.Authorization.WRITE_TEXT_MESSAGE)
            return False

        return True
