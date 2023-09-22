#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

DEFAULT = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text="Расписание"),
        KeyboardButton(text="Профиль")
    ],
    [
        KeyboardButton(text="Д/З [Ближайшее]"),
        KeyboardButton(text="Д/З [Прошедшее]")
    ],
    [
        KeyboardButton(text="Оценки [По дате]"),
        KeyboardButton(text="Оценки [По предмету]")
    ],
    [
        KeyboardButton(text="Настройки"),
        KeyboardButton(text="О проекте")
    ]
], resize_keyboard=True, selective=True)


AUTH_SYSTEMS = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text="Моя Школа")
    ],
    [
        KeyboardButton(text="МЭШ")
    ]
], resize_keyboard=True, selective=True)


AUTH_LOGIN_TYPE = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text="Госуслуги")
    ],
    [
        KeyboardButton(text="Логин и пароль")
    ],
    [
        KeyboardButton(text="AUPD-TOKEN")
    ]
], resize_keyboard=True, selective=True)


YES_OR_NO = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text="Да"),
        KeyboardButton(text="Нет")
    ]
], resize_keyboard=True, selective=True)


ABOUT = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Моя Школа", url="https://myschool.mosreg.ru/"),
        InlineKeyboardButton(text="МЭШ", url="https://school.mos.ru/")
    ],
    [
        InlineKeyboardButton(text="OctoDiary", url="https://github.com/OctoDiary"),
        InlineKeyboardButton(text="OctoDiary-py", url="https://github.com/OctoDiary/OctoDiary-py")
    ],
    [
        InlineKeyboardButton(text="OctoDiary-tg", url="https://github.com/OctoDiary/OctoDiary-tg"),
        InlineKeyboardButton(text="bxkr", url="https://github.com/bxkr"),
    ],
    [
        InlineKeyboardButton(text="Den4ikSuperOstryyPer4ik", url="https://github.com/Den4ikSuperOstryyPer4ik"),
    ]
])
