from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton


DEFAULT = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text="Расписание"),
        KeyboardButton(text="Оценки"),
    ],
    [
        KeyboardButton(text="Домашние задания"),
        KeyboardButton(text="Профиль")
    ],
    [
        KeyboardButton(text="Настройки"),
        KeyboardButton(text="О проекте")
    ]
], resize_keyboard=True)


AUTH_SYSTEMS = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text="Моя Школа")
    ],
    [
        KeyboardButton(text="МЭШ")
    ]
], resize_keyboard=True)


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
], resize_keyboard=True)


YES_OR_NO = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text="Да"),
        KeyboardButton(text="Нет")
    ]
], resize_keyboard=True)


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


HOMEWORKS_TYPE = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Ближайшие"),
            KeyboardButton(text="Прошедшие"),
        ]
    ],
    resize_keyboard=True
)
