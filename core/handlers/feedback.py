#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import os
import pickle
import random
import re

from aiogram import Router, types, F, Bot
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from core.keyboards.inline import FEEDBACK_PLATFORM, SYSTEMS, DONE, CONFIRM, FEEDBACK_ADMIN_ACTIONS
from core.keyboards.reply import FEEDBACK_REASONS
from core.misc.states import Feedback
from core.misc.texts import Texts
from core.services.database import database

router = Router(name="feedback")


@router.message(Command("feedback"))
async def feedback_cmd(message: types.Message, state: FSMContext):
    if message.chat.type != ChatType.PRIVATE:
        await message.answer(
            text=Texts.Feedback.ONLY_PRIVATE
        )
        return

    await message.answer(
        text=Texts.Feedback.BASE + Texts.Feedback.CHOOSE_SYSTEM,
        reply_markup=FEEDBACK_PLATFORM
    )
    await state.set_state(Feedback.platform)


@router.callback_query(Feedback.platform, F.data.in_(Texts.Feedback.Platforms.keys()))
async def platform(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(platform=call.data)
    await call.message.edit_text(
        text=(
            Texts.Feedback.BASE
            + Texts.Feedback.PLATFORM(PLATFORM=getattr(Texts.Feedback.Platforms, call.data))
            + Texts.Feedback.CHOOSE_SYSTEM
        ),
        reply_markup=SYSTEMS
    )
    await state.set_state(Feedback.system)


@router.callback_query(Feedback.system, F.data.in_(Texts.Systems.values()))
async def system(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(system=call.data)

    await call.message.edit_text(
        text=(
            Texts.Feedback.BASE
            + Texts.Feedback.PLATFORM(PLATFORM=getattr(Texts.Feedback.Platforms, (await state.get_data())["platform"]))
            + Texts.Feedback.SYSTEM(SYSTEM=getattr(Texts.SystemsNames, call.data))
        )
    )
    await call.message.answer(
        text=Texts.Feedback.CHOOSE_REASON,
        reply_markup=FEEDBACK_REASONS
    )
    await state.set_state(Feedback.reason)


@router.message(Feedback.reason, F.text.in_(Texts.Feedback.Reasons.keys()))
async def reason(message: types.Message, state: FSMContext):
    await state.update_data(
        reason=message.text,
        message_thread_id=int(getattr(Texts.Feedback.Reasons, message.text)),
        messages=[]
    )
    await message.answer(
        text=Texts.Feedback.MESSAGES,
        reply_markup=DONE
    )
    await state.set_state(Feedback.messages)


@router.message(Feedback.messages)
async def messages(message: types.Message, state: FSMContext):
    await state.update_data(messages=[
        *(await state.get_data())["messages"],
        message
    ])


@router.callback_query(Feedback.messages, F.data == "done")
async def done(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if len(data["messages"]) == 0:
        await call.answer(text=Texts.Feedback.EMPTY, show_alert=True)
        return

    await call.message.edit_reply_markup()
    await call.message.answer(
        text=Texts.Feedback.CONFIRM,
        reply_markup=CONFIRM
    )
    await state.set_state(Feedback.confirm)


@router.callback_query(Feedback.confirm, F.data == "yes")
async def confirm(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await call.message.edit_reply_markup()
    data = await state.get_data()
    platform = data["platform"]
    system = data["system"]
    messages: list[types.Message] = data["messages"]

    number = random.randint(1000, 99999999)
    while database.get_feedback(number=number) is not None:
        number = random.randint(1000, 99999999)

    msg = await call.message.answer(
        text=Texts.Feedback.SENDING,
        reply_markup=types.ReplyKeyboardRemove()
    )
    database.new_feedback(
        data={
            "number": number,
            "platform": platform,
            "system": system,
            "reason": data["reason"],
            "message_id": msg.message_id,
            "user": call.from_user.id,
            "username": call.from_user.username
        }
    )
    forwarded = await bot.forward_messages(
        chat_id=os.getenv("ADMINS_CHAT_ID"),
        from_chat_id=call.message.chat.id,
        message_ids=[message.message_id for message in messages],
        message_thread_id=data["message_thread_id"],
        disable_notification=True
    )
    await bot.send_message(
        chat_id=os.getenv("ADMINS_CHAT_ID"),
        message_thread_id=data["message_thread_id"],
        reply_to_message_id=forwarded[0].message_id,
        text=Texts.Feedback.NEW(
            NUMBER=number,
            PLATFORM=getattr(Texts.Feedback.Platforms, platform),
            SYSTEM=getattr(Texts.SystemsNames, system),
            USER_ID=call.from_user.id,
            USER_NICK=call.from_user.first_name,
            USERNAME=f"@{call.from_user.username if call.from_user.username else call.from_user.id}",
            TAGS=" ".join([
                Texts.Feedback.TAGS[platform],
                Texts.Feedback.TAGS[system],
                Texts.Feedback.TAGS["user-id"].format(USER_ID=call.from_user.id)
            ]),
        ),
        reply_markup=FEEDBACK_ADMIN_ACTIONS(number, closed=False)
    )
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=Texts.Feedback.SUCCESS(NUMBER=number)
    )
    await msg.delete()


@router.callback_query(Feedback.confirm, F.data == "no")
async def cancel(update: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()
    if isinstance(update, types.CallbackQuery):
        await update.message.delete()

    await (update if isinstance(update, types.Message) else update.message).answer(
        text=Texts.Feedback.CANCEL,
        reply_markup=types.ReplyKeyboardRemove()
    )


async def save_media(message: types.Message):
    file_id = (
        getattr(message, message.content_type.lower())[-1].file_id
        if message.content_type.lower() == "photo"
        else getattr(message, message.content_type.lower()).file_id
    )
    if await database.redis.exists(str(message.media_group_id)):
        data = pickle.loads(await database.redis.get(str(message.media_group_id)))
        data.append((message.content_type.lower(), file_id))
        await database.redis.set(str(message.media_group_id), pickle.dumps(data), ex=3600 * 24 * 30)
    else:
        await database.redis.set(
            str(message.media_group_id),
            pickle.dumps([(message.content_type.lower(), file_id)]),
            ex=3600 * 24 * 30  # 30 days
        )


@router.message(F.media_group_id, F.chat.id == os.getenv("ADMIN_CHAT_ID"))
async def media_group(message: types.Message):
    database.redis._queue.append(save_media(message)) # noqa


@router.message(Command("fanswer"), F.from_user.id.in_(database.admins), F.chat.id == os.getenv("ADMIN_CHAT_ID"))
async def fanswer(message: types.Message, command: CommandObject, bot: Bot):
    if not command.args or not message.reply_to_message or not (match := re.match(r"#OD(.*)", command.args)):
        await message.react([types.ReactionTypeEmoji(emoji="🤨")])
        return

    data = database.get_feedback(number=int(match.group(1)))
    if not data:
        await message.react([types.ReactionTypeEmoji(emoji="🤨")])
        return

    try:
        if message.reply_to_message.media_group_id:
            if not await database.redis.exists(str(message.reply_to_message.media_group_id)):
                await message.react([types.ReactionTypeEmoji(emoji="🤨")])
                return

            data = pickle.loads(await database.redis.get(str(message.reply_to_message.media_group_id)))
            await bot.send_media_group(
                chat_id=data["user"],
                media=[
                    {
                        "photo": types.InputMediaPhoto,
                        "video": types.InputMediaVideo,
                        "document": types.InputMediaDocument,
                        "audio": types.InputMediaAudio
                    }[media_type](media=file_id)
                    for media_type, file_id in data
                ]
            )
        elif message.reply_to_message.content_type in ("photo", "video", "document", "audio"):
            await message.reply_to_message.copy_to(chat_id=data["user"], caption=Texts.Feedback.ANSWER(
                NUMBER=data["number"],
                ANSWER=message.reply_to_message.html_text,
            ))
            return await message.react([types.ReactionTypeEmoji(emoji="👀")])

        await bot.send_message(
            chat_id=data["user"],
            text=Texts.Feedback.ANSWER(
                NUMBER=data["number"],
                ANSWER=message.reply_to_message.html_text,
            )
        )

        await message.react([types.ReactionTypeEmoji(emoji="👀")])
    except Exception as e:
        await message.react([types.ReactionTypeEmoji(emoji="💔")])
        await message.reply(Texts.Feedback.ERROR(e))


@router.message(Command("fanswer"), F.from_user.id.not_in(database.admins))
async def fanswer_fake(message: types.Message):
    await message.react([types.ReactionTypeEmoji(emoji="👏")])


@router.callback_query(F.data.regexp(r"f:close:(\d+)").as_("match"), F.from_user.id.in_(database.admins))
async def fclose(call: types.CallbackQuery, match: re.Match):
    data = database.get_feedback(number=int(match.group(1)))
    if not data:
        await call.answer(text=Texts.Feedback.ALREADY_CLOSED)
        return

    database.clear(number=data["number"])

    await call.message.edit_reply_markup(
        reply_markup=FEEDBACK_ADMIN_ACTIONS(data["number"], close=True)
    )
    await call.answer(text=Texts.Feedback.CLOSED)
