#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from aiogram.fsm.state import StatesGroup, State


class Feedback(StatesGroup):
    platform = State()
    system = State()
    reason = State()
    messages = State()
    confirm = State()


class Authorization(StatesGroup):
    system = State()
    method = State()
    auth_type = State()

    web = State()
    username = State()
    password = State()
    token = State()

    gosuslugi_mfa = State()
    gosuslugi_captcha = State()
    blitz_otp = State()

    confirm = State()
