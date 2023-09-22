#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date
import inspect
import logging
import os
import re
import signal
import sys
from typing import Union

from aiogram import types
from database import Database
from octodiary.exceptions import APIError


def handler(fsm: bool = False):
    def decorator(func):
        async def wrapper(
            update: Union[
                types.Message,
                types.CallbackQuery,
                types.InlineQuery,
                types.ChosenInlineResult
            ],
            *args,
            **kwargs
        ):
            if Database().closed:
                TEXT = "🔴 <b>Бот временно отключен</b>.\n🛠 Ведутся <b>технические работы</b>..."
                if fsm:
                    try:
                        await kwargs["state"].clear()
                    except Exception:
                        pass
                return (
                    await update.answer(TEXT)
                    if isinstance(update, types.Message)
                    else await update.answer(re.sub(r"</?.*>", "", TEXT), show_alert=True)
                    if isinstance(update, types.CallbackQuery)
                    else await update.bot.edit_message_text(text=TEXT, inline_message_id=update.inline_message_id)
                    if isinstance(update, types.ChosenInlineResult) and bool(update.inline_message_id)
                    else await update.answer(
                        [
                            types.InlineQueryResultArticle(
                                id="bot_is_close",
                                title="🔴 Бот временно отключен",
                                input_message_content=types.InputTextMessageContent(
                                    message_text=TEXT
                                ),
                                thumbnail_url="https://img.icons8.com/stickers/100/backend-development.png",
                                description="🛠 Ведутся тех. работы..."
                            )
                        ], 30, True
                    )
                )
            
            try:
                return await func(update, *args, **{
                    attr: value
                    for attr, value in kwargs.items()
                    if attr in inspect.signature(func).parameters
                })
            except APIError as e:
                if fsm:
                    try:
                        await kwargs["state"].clear()
                    except Exception:
                        pass
                TEXT = f"❗️ [<code>{e.status_code}</code>] Сервер ответил <b>ошибкой</b>: <code>{e.error_type}</code>\n\nПопробуйте повторить запрос <b>позже</b>."
                return (
                    await update.answer(TEXT)
                    if isinstance(update, types.Message)
                    else await update.answer(re.sub(r"</?.*>", "", TEXT), show_alert=True)
                    if isinstance(update, types.CallbackQuery)
                    else await update.bot.edit_message_text(text=TEXT, inline_message_id=update.inline_message_id)
                    if isinstance(update, types.ChosenInlineResult) and bool(update.inline_message_id)
                    else await update.answer(
                        [
                            types.InlineQueryResultArticle(
                                id="server_error",
                                title=f"❗️[{e.status_code}] Сервер выдал ошибку",
                                input_message_content=types.InputTextMessageContent(
                                    message_text=TEXT
                                ),
                                thumbnail_url="https://img.icons8.com/color/100/error--v1.png",
                                description="Попробуйте повторить запрос позже."
                            )
                        ], 30, True
                    )
                )
            except (Exception, BaseException) as e:
                logging.exception(e)
        return wrapper
    return decorator


def pluralization_string(number: int, words: list[str]):
    """
    >>> self.utils.pluralization_string(num, ["жизнь", "жизни", "жизней"])
    >>> self.utils.pluralization_string(num, ["рубль", "рубля", "рублей"])
    >>> self.utils.pluralization_string(num, ["ручка", "ручки", "ручек"])
    >>> self.utils.pluralization_string(num, ["апельсин", "апельсина", "апельсинов"])
    """
    if number % 10 == 1 and number % 100 != 11:
        return f"{number} {words[0]}"
    elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
        return f"{number} {words[1]}"
    else:
        return f"{number} {words[2]}"


def restart():
    signal.signal(
        signal.SIGTERM,
        (
            lambda *_: os.execl(
                sys.executable,
                sys.executable,
                "main.py",
                *sys.argv[1:],
            )
        )
    )
    os.killpg(os.getpgid(os.getpid()), signal.SIGTERM)

def sort_dict_dy_date(dictionary: dict, reverse: bool = False, separator: str = ".") -> dict:
    """
    Отсортировать словарь по датам
    >>> sort_dict_by_date({"19.09": ..., "10.09": ..., "02.08": ..., "25.12": ...})
    {'02.08': ..., '10.09': ..., '19.09': ..., '25.12': ...}
    """
    today = date.today()
    return {
        "strings": dict(
            sorted(
                dictionary.items(),
                key=lambda x: tuple(map(int, x[0].split(separator)[::-1])),
                reverse=reverse
            )
        ),
        "current_page": (
            cur
            if (cur := f"{today.day:02}{separator}{today.month:02}") in list(dictionary.keys())
            else 1
        )
    }

def mark(value: str, weight: int) -> str:
    weights = {
        "1": "₁",
        "2": "₂",
        "3": "₃",
        "4": "₄",
        "5": "₅",
        "6": "₆",
        "7": "₇",
        "8": "₈",
        "9": "₉",
    }
    return f"{value}{weights[str(weight)]}"
