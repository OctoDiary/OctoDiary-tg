#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import random

from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InlineKeyboardMarkup, InlineKeyboardButton, \
    InputTextMessageContent, InlineQueryResultsButton

from core.misc.texts import Texts
from core.services.database import database

router = Router(name="Inline")


@router.inline_query(F.query.strip() == "")
async def inline_query(update: InlineQuery):
    user = database.user(update.from_user.id)

    return await update.answer(
        [
            InlineQueryResultArticle(
                id=result_item.id,
                title=result_item.title(random.choice(result_item.emojis)),
                description=result_item.description,
                thumbnail_url=result_item.thumbnail_url,
                reply_markup=result_item.reply_markup or InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=Texts.CLICK_TO_LOAD,
                                callback_data=result_item.id
                            )
                        ]
                    ]
                ),
                input_message_content=InputTextMessageContent(
                    message_text=result_item.message_text(
                        random.choice(result_item.emojis)
                    )
                )
            )
            for res_name in Texts.Inline
            if (result_item := getattr(Texts.Inline, res_name))
            and (
                (result_item["type"] == "authorized" and user.token)
                or result_item["type"] == "all"
                or (result_item["type"] == "unauthorized" and not user.token)
            )
        ],
        cache_time=5,
        is_personal=True,
        button=InlineQueryResultsButton(
            **Texts.INLINE_QUERY_RESULTS_BUTTON
        ),
        switch_pm_text="⚙️ Настройки",
        switch_pm_parameter="settings"
    )
