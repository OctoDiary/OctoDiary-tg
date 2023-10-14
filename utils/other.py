#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import contextlib
import inspect
import logging
import os
import re
import signal
import sys
from datetime import date
from typing import Any, Union

from aiogram import types
from git import Repo

from database import Database
from octodiary.exceptions import APIError
from utils.texts import Texts


def handler(fsm: bool = False):
    """
    Decorator that handles API calls and database checks.

    Args:
        fsm (bool): Whether to clear the state if the bot is closed or func raised exception.

    Returns:
        decorator: The decorator function.

    """
    def decorator(func):
        """
        Wrapper function that handles API calls and database checks.

        Args:
            update (Union[types.Message, types.CallbackQuery, types.InlineQuery, types.ChosenInlineResult]): 
                The update object received from the bot.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Any: The result of the decorated function.

        """
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
            """
            Wrapper function that handles API calls and database checks.

            Args:
                update (Union[types.Message, types.CallbackQuery, types.InlineQuery, types.ChosenInlineResult]): 
                    The update object received from the bot.
                *args: Additional positional arguments.
                **kwargs: Additional keyword arguments.

            Returns:
                Any: The result of the decorated function.

            """
            # Skip func if there is no user or apis
            func_params = inspect.signature(func).parameters
            if (
                "user" in func_params
                and not kwargs.get("user")
            ) or (
                "apis" in func_params
                and not kwargs.get("apis")
            ):
                return
            
            # Check if the bot is closed in the database
            if Database().closed:
                text = Texts.BOT_IS_CLOSED_MESSAGE
                if fsm:
                    with contextlib.suppress(Exception):
                        await kwargs["state"].clear()
                return (
                    await update.answer(text)
                    if isinstance(update, types.Message)
                    else await update.answer(re.sub(r"</?.*>", "", text), show_alert=True)
                    if isinstance(update, types.CallbackQuery)
                    else await update.bot.edit_message_text(text=text, inline_message_id=update.inline_message_id)
                    if isinstance(update, types.ChosenInlineResult) and bool(update.inline_message_id)
                    else await update.answer(
                        [
                            types.InlineQueryResultArticle(
                                id=Texts.BotIsClosedInline.ID,
                                title=Texts.BotIsClosedInline.TITLE,
                                input_message_content=types.InputTextMessageContent(
                                    message_text=text
                                ),
                                thumbnail_url=Texts.BotIsClosedInline.THUMBNAIL,
                                description=Texts.BotIsClosedInline.DESCRIPTION
                            )
                        ], 30, True
                    )
                )

            try:
                
                # Call the decorated function
                return await func(update, *args, **{
                    attr: value
                    for attr, value in kwargs.items()
                    if attr in func_params
                })
            except APIError as e:
                if fsm:
                    with contextlib.suppress(Exception):
                        await kwargs["state"].clear()
                text = Texts.API_ERROR(ERROR=e)
                return (
                    await update.answer(text)
                    if isinstance(update, types.Message)
                    else await update.answer(re.sub(r"</?.*>", "", text), show_alert=True)
                    if isinstance(update, types.CallbackQuery)
                    else await update.bot.edit_message_text(text=text, inline_message_id=update.inline_message_id)
                    if isinstance(update, types.ChosenInlineResult) and bool(update.inline_message_id)
                    else await update.answer(
                        [
                            types.InlineQueryResultArticle(
                                id=Texts.APIErrorInline.ID,
                                title=Texts.APIErrorInline.TITLE(ERROR=e),
                                input_message_content=types.InputTextMessageContent(
                                    message_text=text
                                ),
                                thumbnail_url=Texts.APIErrorInline.THUMBNAIL,
                                description=Texts.APIErrorInline.DESCRIPTION
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
    Returns a pluralized string based on the given number.

    Args:
        number (int): The number to determine the plural form.
        words (list[str]): A list of words representing the singular, dual, and plural forms.

    Returns:
        str: The pluralized string based on the given number.

    Examples:
        >>> pluralization_string(num, ["жизнь", "жизни", "жизней"])
        >>> pluralization_string(num, ["рубль", "рубля", "рублей"])
        >>> pluralization_string(num, ["ручка", "ручки", "ручек"])
        >>> pluralization_string(num, ["апельсин", "апельсина", "апельсинов"])
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


def sort_dict_by_date(dictionary: dict[str, Any], reverse: bool = False, separator: str = ".") -> dict[str, Any]:
    """
    Sort a dictionary by dates.

    Args:
        dictionary: The dictionary to be sorted.
        reverse: If True, sort the dictionary in descending order. Default is False.
        separator: The separator used in the date strings. Default is ".".

    Returns:
        The sorted dictionary.

    Example:
        >>> sort_dict_by_date({"19.09": ..., "10.09": ..., "02.08": ..., "25.12": ...})
        {'02.08': ..., '10.09': ..., '19.09': ..., '25.12': ...}
    """
    today = date.today()

    sorted_dict = dict(
        sorted(
            dictionary.items(),
            key=lambda x: tuple(map(int, x[0].split(separator)[::-1])),
            reverse=reverse
        )
    )

    current_page = (
        cur
        if (cur := f"{today.day:02}{separator}{today.month:02}") in list(dictionary.keys())
        else 1
    )

    return {
        "strings": sorted_dict,
        "current_page": current_page
    }


def mark(value: str, weight: int) -> str:
    """
    Converts a given value to a marked version by appending a subscript number to it.

    Args:
        value (str): The value to be marked.
        weight (int): The weight of the subscript number.

    Returns:
        str: The marked value with the subscript number.
    """
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


def get_hash():
    try:
        hash_ = Repo().head.commit.hexsha
        version = Repo().head.commit.message.splitlines()[0]
        return f'<a href="https://github.com/OctoDiary/OctoDiary-tg/commit/{hash_}">#{hash_[:7]} (<b>{version}</b>)</a>'
    except Exception:
        return "<a href='https://github.com/OctoDiary/OctoDiary-tg'>#last-commit</a>"
