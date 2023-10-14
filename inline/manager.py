#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import functools
import logging
import secrets
from datetime import datetime
from typing import Callable, List, Optional, Union
from urllib.parse import urlparse
from utils.texts import Texts

from aiogram import Bot, Dispatcher, F, Router, types

from inline.types import ButtonCallback
from loop import loop

logger = logging.getLogger("BotInlineManager")

ReplyMarkup = Union[list[list[dict]], list[dict], dict]
Strings = Union[
    list[str],
    dict[str, str]
]


class BotInlineManager:
    """Bot full inline manager"""

    def __init__(self, bot: Bot, dispatcher: Dispatcher, routers: list[Router]):
        self.bot = bot
        self.dispatcher = dispatcher

        self.bot.inline = self.bot.inline_manager = self.dispatcher.inline = self.dispatcher.inline_manager = self


        @dispatcher.startup()
        @loop(60)
        async def loop_clear_maps(**kwargs):
            for data, callback in self.inline_buttons_map.copy().items():
                if callback.delete_time <= datetime.now():
                    del self.inline_buttons_map[data]

        self.inline_buttons_map: dict[str, ButtonCallback] = {}
        self.chosen_inline_results_map = {}

        self.router = Router(name="BotInlineManager")
        self.router.callback_query.register(
            self.callback_query_handler
        )
        self.routers = [*routers, self.router]
        self.dispatcher.include_routers(*self.routers)


    async def callback_query_handler(self, call: types.CallbackQuery):
        if call.data in self.inline_buttons_map:
            await self.inline_buttons_map[call.data].run_callback(call)
            del self.inline_buttons_map[call.data]
        else:
            return await call.answer(
                text=Texts.CALLBACK_DEADLINED,
                show_alert=True
            )

    async def __answer_callback(
        self,
        call: types.CallbackQuery,
        text: str,
        show_alert: bool,
        **kwargs
    ):
        return await call.answer(
            text=text, show_alert=show_alert, **kwargs
        )

    async def validate_inline_markup(
        self,
        buttons: Optional[
            Union[
                types.InlineKeyboardMarkup,
                ReplyMarkup
            ]
        ]
    ):
        return buttons if isinstance(buttons, types.InlineKeyboardMarkup) or not (
            not buttons
            or not isinstance(buttons, (list, dict))
            or not all(all(isinstance(button, dict) for button in row) for row in buttons)
            or not all(
                all(
                    "text" in button
                    or "url" in button
                    or "callback_data" in button
                    or "web_app" in button
                    or "login_url" in button
                    or "switch_inline_query" in button
                    or "switch_inline_query_current_chat" in button
                    or "switch_inline_query_chosen_chat" in button
                    or "callback_game" in button
                    or "pay" in button
                    or "callback" in button
                    or "user_id" in button
                    for button in row
                )
                for row in buttons
            )
        ) else None

    def normalize_markup(self, markup: ReplyMarkup) -> ReplyMarkup:
        return (
            [[markup]]
            if isinstance(markup, dict)
            else [markup]
            if isinstance(markup, list) and any(
                isinstance(i, dict) for i in markup
            )
            else markup
        )

    def generate_markup(self, markup: Optional[ReplyMarkup], *, disable_deadline: bool = False) -> Optional[types.InlineKeyboardMarkup]:
        """Generate ``aiogram.types.InlineKeyboardMarkup`` from ``CustomMarkupType (ReplyMarkup)``"""
        if not markup:
            return None
        elif not isinstance(markup, (list, dict)):
            return markup

        keyboard = []
        markup_map = self.normalize_markup(markup)

        for row in markup_map:
            for button in row:
                if not isinstance(button, dict):
                    continue

                if "callback" not in button and (answer := button.get("answer", {})):
                    button["callback"] = functools.partial(
                        self.__answer_callback,
                        show_alert=answer.get("show_alert", False),
                        text=answer.get("text", answer.get("message", None)),
                        url=answer.get("url", None),
                        cache_time=answer.get("cache", answer.get("cache_time", None))
                    )

                if "callback_data" not in button:
                    button["callback_data"] = button.get("data", secrets.token_hex(8))


        for row in markup_map:
            line = []
            for button in row:
                if not button:
                    continue

                if isinstance(button, types.InlineKeyboardButton):
                    line.append(button)
                    continue

                try:
                    if "url" in button:
                        try:
                            _ = bool(urlparse(button["url"]).netloc)
                        except Exception:
                            return False

                        line.append(
                            types.InlineKeyboardButton(
                                text=button["text"],
                                url=button["url"]
                            )
                        )
                    elif "callback" in button:
                        line.append(
                            types.InlineKeyboardButton(
                                text=button["text"],
                                callback_data=button["callback_data"],
                            )
                        )
                        self.inline_buttons_map[button["callback_data"]] = ButtonCallback.init(
                            data=button["callback_data"],
                            text=button["text"],
                            callback=button["callback"],
                            disable_deadline=disable_deadline,
                            *button.get("args", ()),
                            **button.get("kwargs", {})
                        )
                    elif "user_id" in button:
                        line.append(
                            types.InlineKeyboardButton(
                                text=button["text"],
                                url=f"tg://user?id={button['user_id']}"
                            )
                        )
                    elif "switch_inline_query_current_chat" in button:
                        line.append(
                            types.InlineKeyboardButton(
                                text=button["text"],
                                switch_inline_query_current_chat=button["switch_inline_query_current_chat"]
                            )
                        )
                    elif "switch_inline_query" in button:
                        line.append(
                            types.InlineKeyboardButton(
                                text=button["text"],
                                switch_inline_query=button["switch_inline_query"]
                            )
                        )
                    elif "switch_inline_query_chosen_chat" in button:
                        line.append(
                            types.InlineKeyboardButton(
                                text=button["text"],
                                switch_inline_query_chosen_chat=(
                                    button["switch_inline_query_chosen_chat"]
                                    if isinstance(
                                        button["switch_inline_query_chosen_chat"],
                                        types.SwitchInlineQueryChosenChat
                                    )
                                    else types.SwitchInlineQueryChosenChat(
                                        query=button["switch_inline_query_chosen_chat"].get("query"),
                                        allow_user_chats=button["switch_inline_query_chosen_chat"].get("allow_user_chats"),
                                        allow_bot_chats=button["switch_inline_query_chosen_chat"].get("allow_bot_chats"),
                                        allow_group_chats=button["switch_inline_query_chosen_chat"].get("allow_group_chats"),
                                        allow_channel_chats=button["switch_inline_query_chosen_chat"].get("allow_channel_chats")
                                    ) if isinstance(button["switch_inline_query_chosen_chat"], dict) else None
                                )
                            )
                        )
                    else:
                        line.append(
                            types.InlineKeyboardButton(
                                text=button["text"],
                                callback_data=button["callback_data"]
                            )
                        )
                except KeyError:
                    return

            if line:
                keyboard.append(line)

        return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Union[ReplyMarkup, types.InlineKeyboardMarkup]] = None,
        **kwargs
    ):
        return await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=self.generate_markup(reply_markup),
            **kwargs
        )

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[Union[ReplyMarkup, types.InlineKeyboardMarkup]] = None,
        **kwargs
    ):
        return await self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=self.generate_markup(reply_markup),
            **kwargs
        )

    async def edit_message_reply_markup(
        self,
        chat_id: int,
        message_id: int,
        reply_markup: Optional[Union[ReplyMarkup, types.InlineKeyboardMarkup]] = None,
        **kwargs
    ):
        return await self.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=self.generate_markup(reply_markup),
            **kwargs
        )

    async def send_photo(
        self,
        chat_id: int,
        photo: Union[str, types.InputFile],
        caption: Optional[str] = None,
        reply_markup: Optional[Union[ReplyMarkup, types.InlineKeyboardMarkup]] = None,
        **kwargs
    ):
        return await self.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            reply_markup=self.generate_markup(reply_markup),
            **kwargs
        )


    def _list_markup(self, *args, **kwargs):
        return (lambda: self._inline_list_markup(*args, **kwargs))

    def chunks(self, lst, n):
        return [lst[i : i + n] for i in range(0, len(lst), n)]

    def _inline_list_markup(
        self,
        strings: Strings,
        current_page: Union[int, str] = 1,
        row_width: int = 3,
        rows: Optional[ReplyMarkup] = None
    ):
        if isinstance(strings, dict):
            return self.generate_markup(
                self.chunks([
                    {
                        "text": (
                            f"· {btn} ·" if (
                                btn == current_page
                            ) else btn
                        ),
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[btn],
                            "markup": self._list_markup(strings, list(strings.keys())[num], row_width, rows)
                        }
                    }
                    for num, btn in enumerate(list(strings.keys()))
                ], row_width)
            )
        else:
            current = (current_page if isinstance(current_page, int) else strings.index(current_page)+1)
            return self.generate_markup(
                [
                    {
                        "text": str(num) if num != current else f"· {num} ·",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[num-1],
                            "markup": self._list_markup(strings, num, row_width, rows)
                        }
                    }
                    for num in range(1, len(strings)+1)
                ] if len(strings) <= 5 else [
                    {
                        "text": f"· {num} ·",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[num-1],
                            "markup": self._list_markup(strings, num, row_width, rows)
                        }
                    } if num == current else {
                        "text": f"{num} ›",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[num-1],
                            "markup": self._list_markup(strings, num, row_width, rows)
                        }
                    } if num == 4 else {
                        "text": f"{len(strings)} »",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[-1],
                            "markup": self._list_markup(strings, len(strings), row_width, rows)
                        }
                    } if num == 5 else {
                        "text": str(num),
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[num-1],
                            "markup": self._list_markup(strings, num, row_width, rows)
                        }
                    }
                    for num in range(1, 6)
                ] if current <= 3 else [
                    {
                        "text": f"« {1}",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[0],
                            "markup": self._list_markup(strings, 1, row_width, rows)
                        }
                    },
                    *[
                        {
                            "text": f"· {num} ·" if num == current else str(num),
                            "callback": self._list_callback,
                            "kwargs": {
                                "new_text": strings[num-1],
                                "markup": self._list_markup(strings, num, row_width, rows)
                            }
                        }
                        for num in range(len(strings)-2, len(strings)+1)
                    ]
                ] if current > len(strings)-3 else [
                    {
                        "text": f"« {1}",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[0],
                            "markup": self._list_markup(strings, 1, row_width, rows)
                        }
                    },
                    {
                        "text": f"‹ {current-1}",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[current-2],
                            "markup": self._list_markup(strings, current-1, row_width, rows)
                        }
                    },
                    {
                        "text": f"· {current} ·",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[current-1],
                            "markup": self._list_markup(strings, current, row_width, rows)
                        }
                    },
                    {
                        "text": f"{current+1} ›",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[current],
                            "markup": self._list_markup(strings, current+1, row_width, rows)
                        }
                    },
                    {
                        "text": f"{len(strings)} »",
                        "callback": self._list_callback,
                        "kwargs": {
                            "new_text": strings[-1],
                            "markup": self._list_markup(strings, len(strings), row_width, rows)
                        }
                    }
                ]
            )

    async def list(
        self,
        update: Union[
            types.Message,
            types.ChosenInlineResult,
            types.CallbackQuery,
            types.Chat,
            types.User,
        ],
        strings: Strings,
        row_width: int = 3,
        current_page: Union[int, str] = 1,
        *,
        disable_deadline: bool = False,
        **kwargs
    ):
        first = (
            (
                strings
                if isinstance(strings, list)
                else list(strings.values())
            )[current_page-1]
            if isinstance(current_page, int)
            else strings[current_page]
        )


        return await self.answer(
            update=update,
            response=first,
            reply_markup=self._inline_list_markup(
                strings,
                current_page
                if current_page and (isinstance(current_page, int) and isinstance(strings, list)) or (isinstance(current_page, str) and isinstance(strings, dict))
                else 1
                if isinstance(strings, list)
                else next(iter(strings.keys())),
                row_width
            ),
            disable_deadline=disable_deadline,
            **kwargs
        )

    async def _list_callback(self, call: types.CallbackQuery, new_text: str, markup: Callable[..., types.InlineKeyboardMarkup]):
        return await self.answer(
            update=call,
            response=new_text,
            reply_markup=markup()
        )


    async def answer(
        self,
        update: Union[
            types.Message,
            types.ChosenInlineResult,
            types.CallbackQuery,
            types.Chat,
            types.User,
        ],
        response: Union[str, List[str]],
        reply_markup: Optional[Union[
            ReplyMarkup,
            types.InlineKeyboardMarkup,
            types.ReplyKeyboardRemove,
            types.ReplyKeyboardMarkup,
        ]],
        *,
        disable_deadline: bool = False,
        **kwargs
    ):
        if isinstance(reply_markup, (list, dict)):
            new_reply_markup = self.generate_markup(reply_markup, disable_deadline=disable_deadline)
        else:
            new_reply_markup = reply_markup

        if isinstance(update, types.Message):
            edit = (update.from_user.id == self.bot.id and not update.forward_date)
            if isinstance(response, str):
                return await (update.edit_text if edit else update.answer)(
                    text=response,
                    reply_markup=new_reply_markup,
                    **kwargs
                )
            else:
                return await self.list(update, response, **kwargs)
        elif isinstance(update, types.CallbackQuery):
            if update.inline_message_id:
                return await self.bot.edit_message_text(
                    text=response,
                    inline_message_id=update.inline_message_id,
                    reply_markup=new_reply_markup, **kwargs
                )
            else:
                return await update.message.edit_text(
                    text=response,
                    reply_markup=new_reply_markup, **kwargs
                )
        elif isinstance(update, (types.Chat, types.User)):
            return await self.bot.send_message(
                text=response,
                chat_id=update.id,
                reply_markup=new_reply_markup, **kwargs
            )
        elif isinstance(update, types.ChosenInlineResult) and update.inline_message_id:
            return await self.bot.edit_message_text(
                text=response,
                inline_message_id=update.inline_message_id,
                reply_markup=new_reply_markup, **kwargs
            )

        return False
