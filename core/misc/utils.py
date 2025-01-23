#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import functools
import os
import re
import signal
import sys
import typing
from datetime import datetime, timezone, timedelta, date
from urllib.parse import quote_plus, unquote_plus

from git import Repo

TIMEZONE = timezone(timedelta(hours=3), "MSK")


def get_hash():
    try:
        hash_ = Repo().head.commit.hexsha
        return f'<a href="https://github.com/OctoDiary/OctoDiary-tg/commit/{hash_}">#{hash_[:7]}</a>'
    except Exception:
        return "<a href='https://github.com/OctoDiary/OctoDiary-tg'>#last-version</a>"


def get_date():
    return get_datetime().date()


def get_datetime():
    return datetime.now(tz=TIMEZONE)


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


def get_week_for_date(input_date) -> list[date]:
    start_of_week = input_date - timedelta(days=input_date.weekday())

    return [
        start_of_week + timedelta(days=i)
        for i in range(7)
    ]


def chunks(_list: typing.Union[list, set, tuple], n: int, /) -> typing.List[typing.List[typing.Any]]:
    """
    From https://github.com/hikariatama/Hikka/blob/master/hikka/utils.py#L879

    Split provided `_list` into chunks of `n`
    :param _list: List to split
    :param n: Chunk size
    :return: List of chunks
    """
    return [_list[i : i + n] for i in range(0, len(_list), n)]


WEEKDAY = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье"
]

MONTH_NAMES = [
    "...",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]

MONTH_NAME_NUMERALS = [
    "...",
    "Января",
    "Февраля",
    "Марта",
    "Апреля",
    "Мая",
    "Июня",
    "Июля",
    "Августа",
    "Сентября",
    "Октября",
    "Ноября",
    "Декабря",
]


def start_with_args(args: str) -> str:
    return f"https://t.me/OctoDiary{'Test' if os.getenv('TEST') else ''}Bot?start={args}"


def fmark(value: str, weight: int) -> str:
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


def urlencoded(url: str) -> str:
    return quote_plus(url)


def urldecode(url: str) -> str:
    return unquote_plus(url)


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse_time(dt, seconds: bool = False) -> str:
    try:
        return re.match(
            r"^((?:(\d{4}-\d{2}-\d{2}).(\d{2}:\d{2}:\d{2}(?:\.\d+)?))(Z|[\+-]\d{2}:\d{2})?)$",
            str(dt)
        ).group(3)[:5 if not seconds else 8]
    except:
        return "00:00" if not seconds else "00:00:00"


def parse_date_iso(dt, year: bool = True) -> str:
    try:
        return re.match(
            r"^(\d{4}-\d{2}-\d{2})",
            str(dt)
        ).group(1)[5 if not year else 0:]
    except:
        return "01.01.2025"


def run_sync(func, *args, **kwargs):
    """
    https://github.com/hikariatama/Hikka/blob/c13cd19d1293d868bc1c6776d0d659f98f4201f2/hikka/utils.py#L305
    Run a non-async function in a new thread and return an awaitable
    :param func: Sync-only function to execute
    :return: Awaitable coroutine
    """
    return asyncio.get_event_loop().run_in_executor(
        None,
        functools.partial(func, *args, **kwargs),
    )


def run_async(loop: asyncio.AbstractEventLoop, coro: typing.Awaitable) -> typing.Any:
    """
    https://github.com/hikariatama/Hikka/blob/c13cd19d1293d868bc1c6776d0d659f98f4201f2/hikka/utils.py#L317

    Run an async function as a non-async function, blocking till it's done
    :param loop: Event loop to run the coroutine in
    :param coro: Coroutine to run
    :return: Result of the coroutine
    """
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


def restart():
    signal.signal( # noqa
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


# noinspection Annotator
def sort_dict_by_date(dictionary: dict[str, typing.Any], reverse: bool = False, separator: str = ".") -> dict[str, typing.Any]:
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
