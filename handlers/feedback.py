#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import os

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from utils.texts import Texts

feedback = Router()


class States(StatesGroup):
    platform = State()
    system = State()
    reason = State()
    messages = State()
    confirm = State()


@feedback.message(Command("feedback"))
async def feedback_cmd(message: Message, state: FSMContext):
    await message.answer(
        text=Texts.FEEDBACK.CHOOSE_PLATFORM,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Telegram-бот"),
                    KeyboardButton(text="Android-приложение")
                ]
            ], is_persistent=True, resize_keyboard=True
        )

    )
    await state.set_state(States.platform)


@feedback.message(States.platform)
async def platform(message: Message, state: FSMContext):
    await state.update_data(platform=message.text)
    await message.answer(
        text=Texts.FEEDBACK.CHOOSE_SYSTEM,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=Texts.MY_SCHOOL),
                    KeyboardButton(text=Texts.MES),
                ]
            ], is_persistent=True, resize_keyboard=True
        )

    )
    await state.set_state(States.system)


@feedback.message(States.system)
async def system(message: Message, state: FSMContext):
    await state.update_data(system=message.text)
    await message.answer(
        text=Texts.FEEDBACK.CHOOSE_REASON,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=reason),
                ]
                for reason in Texts.FEEDBACK.REASONS
            ], is_persistent=True, resize_keyboard=True
        )
    )
    await state.set_state(States.reason)


@feedback.message(States.reason)
async def reason(message: Message, state: FSMContext):
    await state.update_data(
        reason=message.text,
        message_thread_id=int(getattr(Texts.FEEDBACK.REASONS, message.text)),
        messages=[]
    )
    await message.answer(
        text=Texts.FEEDBACK.SEND_FEEDBACK,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Готово"),
                ]
            ], is_persistent=True, resize_keyboard=True
        )
    )
    await state.set_state(States.messages)


@feedback.message(States.messages)
async def messages(message: Message, state: FSMContext):
    if message.text != "Готово":
        await state.update_data(messages=[*(await state.get_data())["messages"], message])
    else:
        if len((await state.get_data())["messages"]) == 0:
            await state.clear()
            await message.answer(
                text=Texts.FEEDBACK.NOT_MESSAGES,
                reply_markup=ReplyKeyboardRemove()
            )
            return

        await message.answer(
            text=Texts.FEEDBACK.CONFIRM,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text=Texts.YES),
                        KeyboardButton(text=Texts.NO),
                    ]
                ], is_persistent=True, resize_keyboard=True
            )
        )
        await state.set_state(States.confirm)


@feedback.message(States.confirm)
async def confirm(message: Message, state: FSMContext, bot: Bot):
    if message.text == Texts.YES:
        data = await state.get_data()
        platform = data["platform"]
        system = data["system"]
        messages: list[Message] = data["messages"]

        msg = await message.answer(
            text=Texts.FEEDBACK.SENDING,
            reply_markup=ReplyKeyboardRemove(),
        )

        await bot.send_message(
            chat_id=os.getenv("ADMINS_CHAT_ID"),
            message_thread_id=data["message_thread_id"],
            text=f"""🔰 Новое обращение!\n\n<b>Платформа</b>: {platform}\n<b>Система</b>: {system}\n<b>Автор</b>: {message.from_user.full_name} | <code>{'@' + message.from_user.username if message.from_user.username else message.from_user.id}</code>\n""" + "\n" + " ".join([Texts.FEEDBACK.TAGS[platform], Texts.FEEDBACK.TAGS[system], Texts.FEEDBACK.TAGS["user-id"].format(USER_ID=message.from_user.id)])
        )
        await bot.forward_messages(
            chat_id=os.getenv("ADMINS_CHAT_ID"),
            from_chat_id=message.chat.id,
            message_ids=[m.message_id for m in messages],
            message_thread_id=data["message_thread_id"]
        )

        await msg.delete()
        await message.answer(Texts.FEEDBACK.SENT)
    else:
        await message.answer(
            text=Texts.FEEDBACK.OK,
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
