#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import json

import jwt
from aiogram import Router, types, F, enums, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject

from core.misc.texts import Texts
from core.misc.utils import escape_html
from core.services.api import UserData
from core.services.database import database

router = Router(name="OtherFunctions")


@router.message(Command("html"), F.reply_to_message.is_not(None), F.reply_to_message.html_text.is_not(None))
async def get_html_markdown(message: types.Message):
    text = escape_html(message.reply_to_message.html_text)
    await message.answer(
        f'<pre><code class="language-html">{text}</code></pre>'
    )


@router.message(Command("markdown"), F.reply_to_message.is_not(None), F.reply_to_message.md_text.is_not(None))
async def get_html_markdown(message: types.Message):
    text = escape_html(message.reply_to_message.md_text)
    await message.answer(
        f'<pre><code class="language-markdown">{text}</code></pre>',
        parse_mode=enums.ParseMode.HTML
    )


@router.message(Command("reaction"))
async def reaction(message: types.Message, command: CommandObject):
    if not command.args:
        return

    try:
        await message.react([types.ReactionTypeEmoji(emoji=command.args)])
    except TelegramBadRequest:
        await message.react([types.ReactionTypeEmoji(emoji="👀")])


@router.message(Command("refresh_token"), F.text.regexp(r"\/refresh_token ([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_\-\+\/=]*)"), F.from_user.id.in_(database.admins))
async def refresh_token(message: types.Message, command: CommandObject):
    try:
        token = await UserData.refresh_token(
            token=command.args
        )
        await message.answer(f"<code>{token}</code>")
    except: # noqa
        await message.answer("⚠️ Error. Invalid token?")


@router.message(Command("reload_texts"), F.from_user.id.in_(database.admins))
async def refresh_texts(message: types.Message):
    Texts.reload()
    await message.react([types.ReactionTypeEmoji(emoji="👌")])


@router.message(Command("token_data"), F.text.regexp(r"\/token_data ([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_\-\+\/=]*)"))
async def token_data(message: types.Message, command: CommandObject):
    try:
        data = jwt.decode(command.args, options={"verify_signature": False})
        data = json.dumps(data, indent=4)
        await message.answer(f'<pre><code class="JWT">{data}</code></pre>')
    except: # noqa
        await message.answer("⚠️ Error. Invalid token?")


@router.message(Command("reload_data"))
async def reload_data(message: types.Message, bot: Bot):
    user = database.user(message.from_user.id)
    await UserData(user, user.apis).load_all(bot)
    await message.answer("✅ Data reloaded")


@router.message(Command("string"))
async def string(message: types.Message, command: CommandObject):
    await message.answer(("{" + command.args + "}").format(root=Texts))
