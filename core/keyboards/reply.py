#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from core.misc.texts import Texts


def root_menu(system: Texts.Systems) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [
            KeyboardButton(text=Texts.Buttons.DIARY)
        ]
    ] + (
        [
            [
                KeyboardButton(text=Texts.Buttons.SETTINGS),
                KeyboardButton(text=Texts.Buttons.PROJECT_ABOUT)
            ]
        ] if system == "myschool"
        else [
            [
                KeyboardButton(text=Texts.Buttons.VISITS),
                KeyboardButton(text=Texts.Buttons.SETTINGS),
            ],
            [
                KeyboardButton(text=Texts.Buttons.PROJECT_ABOUT)
            ]
        ] if system == Texts.Systems.MES
        else []
    ), resize_keyboard=True, selective=True)


SYSTEMS = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=Texts.MY_SCHOOL),
            KeyboardButton(text=Texts.MES),
        ]
    ], is_persistent=True, resize_keyboard=True
)

FEEDBACK_REASONS = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=reason)
        ]
        for reason in Texts.Feedback.Reasons
    ], is_persistent=True, resize_keyboard=True
)

DONE = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=Texts.Buttons.DONE)
        ]
    ], is_persistent=True, resize_keyboard=True
)

CONFIRM = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=Texts.YES),
            KeyboardButton(text=Texts.NO)
        ]
    ], is_persistent=True, resize_keyboard=True
)

CANCEL = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=Texts.Buttons.CANCEL)
        ]
    ], is_persistent=True, resize_keyboard=True
)
