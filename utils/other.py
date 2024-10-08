#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import contextlib
import inspect
import os
import re
import signal
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Union

from aiogram import types
from aiogram.types import BufferedInputFile
from git import Repo
from loguru import logger

from database import Database, User
from octodiary.apis import AsyncMobileAPI
from octodiary.exceptions import APIError
from octodiary.types import Type
from octodiary.urls import Systems
from utils.texts import Texts


def handler(*, fsm: bool = False):
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
            func: The function to be decorated.

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
            func_params = list(inspect.signature(func).parameters.keys())
            if func_params == ["args", "kwargs"]:
                func_params = func.params
            else:
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
                dt = get_datetime()
                system = Database().user(str(update.from_user.id)).system
                logger.bind(
                    user_id=update.from_user.id,
                    username=update.from_user.username,
                    system=system
                ).exception(e)
                error_message = await update.bot.send_message(update.from_user.id, Texts.INTERNAL_ERROR)
                await update.bot.send_chat_action(update.from_user.id, "upload_document")
                await update.bot.send_document(update.from_user.id, BufferedInputFile.from_file(
                    "user_error.log",
                    filename=f"user_error_{system}_{dt.strftime('%Y-%m-%d_%H-%M')}.log"
                ), reply_to_message_id=error_message.message_id)
                with open("user_error.log", encoding="utf-8", mode="w") as f:
                    f.write("")
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
        >>> num = 5
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
        >>> data = {"19.09": ..., "10.09": ..., "02.08": ..., "25.12": ...}
        >>> sort_dict_by_date(data)
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
        return f'<a href="https://github.com/OctoDiary/OctoDiary-tg/commit/{hash_}">#{hash_[:7]}</a>'
    except Exception:
        return "<a href='https://github.com/OctoDiary/OctoDiary-tg'>#last-commit</a>"


TIMEZONE = timezone(timedelta(hours=3), "MSK")


def get_date():
    return get_datetime().date()


def get_datetime():
    return datetime.now(tz=TIMEZONE)


class ODAuth(Type):
    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str


async def refresh_mes_token(user: User, *, is_expired: bool = False):
    _api = AsyncMobileAPI(system=Systems.MES)
    if is_expired:
        auth_settings: ODAuth = ODAuth(**user.db_od_auth)
        token = await _api.refresh_token(
            token=auth_settings.refresh_token,
            client_id=auth_settings.client_id,
            client_secret=auth_settings.client_secret
        )
        user.token = token
        new_auth = ODAuth(
            access_token=token,
            refresh_token=_api.token_for_refresh,
            client_id=auth_settings.client_id,
            client_secret=auth_settings.client_secret
        )
        await _api.edit_user_settings_app(
            settings=new_auth,
            profile_id=user.db_profile_id,
            name="od_auth"
        )
    else:
        api = AsyncMobileAPI(system=Systems.MES, token=user.token)
        try:
            auth_settings = await api.get_user_settings_app(
                profile_id=user.db_profile_id,
                name="od_auth",
                settings_model=ODAuth
            )
        except APIError as e:
            if e.status_code == 401:
                return await refresh_mes_token(user, is_expired=True)
            else:
                raise e

        if auth_settings.access_token != user.token:
            user.token = auth_settings.access_token
        else:
            _api = AsyncMobileAPI(system=Systems.MES)
            token = await _api.refresh_token(
                token=auth_settings.refresh_token,
                client_id=auth_settings.client_id,
                client_secret=auth_settings.client_secret
            )
            user.token = token
            new_auth = ODAuth(
                access_token=token,
                refresh_token=_api.token_for_refresh,
                client_id=auth_settings.client_id,
                client_secret=auth_settings.client_secret
            )
            await _api.edit_user_settings_app(
                settings=new_auth,
                name="od_auth",
                profile_id=user.db_profile_id
            )
            user.db_od_auth = new_auth.model_dump(mode="json")


def start_with_args(args: str) -> str:
    return f"https://t.me/OctoDiary{'Test' if os.getenv('TEST') else ''}Bot?start={args}"
