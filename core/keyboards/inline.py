#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.misc.texts import Texts
from core.misc.utils import chunks, fmark

BACK_BUTTON = lambda name=None: [ # noqa
    [
        InlineKeyboardButton(text=Texts.Buttons.BACK, callback_data=f"{name}:back" if name else "back"),
    ]
]

ABOUT = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text=Texts.MY_SCHOOL, url=Texts.Buttons.MY_SCHOOL_URL),
        InlineKeyboardButton(text=Texts.MES, url=Texts.Buttons.MES_URL)
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

FEEDBACK_PLATFORM = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=text, callback_data=name)
            for name, text in Texts.Feedback.Platforms.items()
        ]
    ]
)

SYSTEMS = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=text, callback_data=name)
            for name, text in Texts.SystemsNames.items()
        ]
    ]
)

DONE = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text=Texts.Buttons.DONE, callback_data="done")
    ]
])

CONFIRM = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text=Texts.YES, callback_data="yes"),
        InlineKeyboardButton(text=Texts.NO, callback_data="no")
    ]
])

FEEDBACK_ADMIN_ACTIONS = lambda number, closed=False: InlineKeyboardMarkup(inline_keyboard=[ # noqa
    [
        InlineKeyboardButton(text=Texts.Buttons.CLOSE if not closed else Texts.Buttons.CLOSED,
                             callback_data=f"f:close:{number}"),
    ]
])

CANCEL = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text=Texts.Buttons.CANCEL, callback_data="cancel")
    ]
])

LOGIN_METHODS_MY_SCHOOL = InlineKeyboardMarkup(inline_keyboard=[
                                                                   [
                                                                       InlineKeyboardButton(text=name,
                                                                                            callback_data=data),
                                                                   ]
                                                                   for data, name in Texts.LoginMethods.items()
                                                               ] + BACK_BUTTON())

DIARY = InlineKeyboardMarkup(inline_keyboard=chunks(
    [
        InlineKeyboardButton(text=name, callback_data=data)
        for data, name in Texts.Diary.Commands.items()
    ], 2
))

CALC_MARKS = lambda _id: InlineKeyboardMarkup(inline_keyboard=list(reversed([
    [
        InlineKeyboardButton(
            text=fmark(value=str(value), weight=weight),
            callback_data=f"calc:{_id}:add:{value}-{weight}"
        )
        for weight in range(1, 5)
    ]
    for value in range(2, 6)
])) + [
                                                                  [
                                                                      InlineKeyboardButton(
                                                                          text=Texts.Calculator.REMOVE_MARK,
                                                                          callback_data=f"calc:{_id}:remove:-"
                                                                      ),
                                                                      InlineKeyboardButton(
                                                                          text=Texts.Calculator.CLEAR_MARKS,
                                                                          callback_data=f"calc:{_id}:clear:-"
                                                                      )
                                                                  ]
                                                              ])
