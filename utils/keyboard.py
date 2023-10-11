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

from utils.texts import Texts

DEFAULT = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text=Texts.Buttons.SCHEDULE),
        KeyboardButton(text=Texts.Buttons.PROFILE)
    ],
    [
        KeyboardButton(text=Texts.Buttons.HOMEWORKS_UPCOMING),
        KeyboardButton(text=Texts.Buttons.HOMEWORKS_PAST)
    ],
    [
        KeyboardButton(text=Texts.Buttons.MARKS_BY_DATE),
        KeyboardButton(text=Texts.Buttons.MARKS_BY_SUBJECT)
    ],
    [
        KeyboardButton(text=Texts.Buttons.SETTINGS),
        KeyboardButton(text=Texts.Buttons.PROJECT_ABOUT)
    ]
], resize_keyboard=True, selective=True)


AUTH_SYSTEMS = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text=Texts.MY_SCHOOL)
    ],
    [
        KeyboardButton(text=Texts.MESH)
    ]
], resize_keyboard=True, selective=True)


AUTH_LOGIN_TYPE = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text=Texts.Gosuslugi)
    ],
    [
        KeyboardButton(text=Texts.LoginAndPassword)
    ],
    [
        KeyboardButton(text=Texts.AUPD_TOKEN)
    ]
], resize_keyboard=True, selective=True)


YES_OR_NO = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text=Texts.YES),
        KeyboardButton(text=Texts.NO)
    ]
], resize_keyboard=True, selective=True)


ABOUT = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text=Texts.MY_SCHOOL, url=Texts.Buttons.MY_SCHOOL_URL),
        InlineKeyboardButton(text=Texts.MESH, url=Texts.Buttons.MESH_URL)
    ],
    [
        InlineKeyboardButton(text="OctoDiary", url=Texts.Buttons.ORGANIZATION_URL),
        InlineKeyboardButton(text="OctoDiary-py", url=Texts.Buttons.PROJECT_LIBRARY_URL)
    ],
    [
        InlineKeyboardButton(text="OctoDiary-tg", url=Texts.Buttons.PROJECT_URL),
        InlineKeyboardButton(text="bxkr", url=Texts.Buttons.bxkr_URL),
    ],
    [
        InlineKeyboardButton(text="Den4ikSuperOstryyPer4ik", url=Texts.Buttons.Den4ikSuperOstryyPer4ik_URL),
    ]
])
