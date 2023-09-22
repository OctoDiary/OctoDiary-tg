#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary


from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from database import Database
from git import Repo
from octodiary.asyncApi.myschool import AsyncMobileAPI
from octodiary.exceptions import APIError
from utils.keyboard import ABOUT, AUTH_LOGIN_TYPE, AUTH_SYSTEMS, DEFAULT, YES_OR_NO
from .myschool._loop import on_startup_myschool_router

router = Router(name="Start")


def get_hash():
    try:
        hash_ = Repo().head.commit.hexsha
        return f'<a href="https://github.com/OctoDiary/OctoDiary-tg/commit/{hash_}">#{hash_[:7]}</a>'
    except Exception:
        return "<a href='https://github.com/OctoDiary/OctoDiary-tg'>#last-commit</a>"



@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        f"""
👋 Привет, <b>{message.from_user.full_name}</b>!

🤖 Я - бот <b>OctoDiary</b>!
Мои возможности <b>обширные</b>:
• Покажу расписание, оценки, домашние задания <b>подробно</b>
• <b>Поддержка</b> системы <a href="https://myschool.mosreg.ru/"><b>Моя Школа</b></a> <tg-spoiler>(</tg-spoiler><a href="https://school.mos.ru/"><tg-spoiler><b>МЭШ</b></tg-spoiler></a><tg-spoiler> - скоро...)</tg-spoiler>
• <b>Уведомлю</b> о новом ДЗ, новой оценке, изменении расписании и т.д.
И это ещё не всё! 

😼 Ну что же, <b>давай начнём</b>! Вводи <b>команду</b> /auth или /login, чтобы <b>авторизоваться</b>!
        """,
        reply_markup=DEFAULT if message.chat.type == ChatType.PRIVATE and Database().user(message.from_user.id).token else None
    )


@router.message(F.text == "О проекте")
async def about(message: Message):
    await message.answer(
        f"""
[<a href='https://github.com/OctoDiary/'><b>OctoDiary</b></a>]
Проект «<a href='https://github.com/OctoDiary/'><b>OctoDiary</b></a>» реализуется двумя разработчиками:
• <a href='https://github.com/Den4ikSuperOstryyPer4ik'><b>Den4ikSuperOstryyPer4ik</b></a>
• <a href='https://github.com/bxkr'><b>bxkr</b></a>
Весь исходный код: <a href='https://github.com/OctoDiary/OctoDiary-tg'><b>OctoDiary-tg</b></a> | <a href='https://github.com/OctoDiary/OctoDiary-py'><b>OctoDiary-py</b></a>
Текущая версия бота: {get_hash()}

[<a href='https://myschool.mosreg.ru/'><b>Моя Школа</b></a>]
Проект «<a href='https://myschool.mosreg.ru/'><b>Моя Школа</b></a>» реализуется Правительством Москвы, Министерством цифрового развития, связи и массовых коммуникаций Российской Федерации, Министерством просвещения Российской Федерации.
        """,
        reply_markup=ABOUT,
        disable_web_page_preview=True
    )


auth_router = Router()

class Form(StatesGroup):
    system = State()
    login_type = State()
    username = State()
    password = State()
    gosuslugi_mfa = State()
    token = State()
    confirm = State()


@auth_router.message(Command(commands=["auth", "login"]))
async def auth(message: Message, state: FSMContext):
    if Database().user(message.from_user.id).token:
        await message.answer("🚫 Вы уже авторизованы!")
        return
    
    await state.set_state(Form.system)
    await message.answer(
        "Выберите <b>систему</b>:",
        reply_markup=AUTH_SYSTEMS,
        resize_keyboard=True
    )


@auth_router.message(Form.system)
async def set_system(message: Message, state: FSMContext):
    match message.text:
        case "МЭШ":
            await state.clear()
            await message.answer(
                "Данная система в настоящее время <b>не поддерживается</b>. <i><tg-spoiler>Скоро...</tg-spoiler></i>",
                reply_markup=ReplyKeyboardRemove()
            )
        case "Моя Школа":
            await state.update_data(
                system="myschool" if message.text == "Моя Школа" else "mesh"
            )
            await state.set_state(Form.login_type)
            await message.answer(
                "Выберите тип логина:",
                reply_markup=AUTH_LOGIN_TYPE
            )


@auth_router.message(Form.login_type)
async def set_login_type(message: Message, state: FSMContext):
    match message.text:
        case "Логин и пароль":
            await state.update_data(login_type="logpass")
            await state.set_state(Form.username)
            await message.answer(
                f"""
✅ <b>Отлично</b>!
Теперь нужно ввести <b>логин и пароль</b> от вашего аккаунта системы <b>«Моя Школа»</b>.

🔒 Мы <b>не сохраняем</b> данные для входа. На сервере будет хранится <b>только токен</b>, доступный исключительно <b>Вам</b>. 
Исходный код <b>текущей</b> версии: {get_hash()}

🔒 Введите <b>логин</b>:
                """,
                disable_web_page_preview=True,
                reply_markup=ReplyKeyboardRemove()
            )
        case "Госуслуги":
            await state.update_data(login_type="gosuslugi")
            await state.set_state(Form.username)
            await message.answer(
                f"""
✅ <b>Отлично</b>!
Теперь нужно ввести <b>логин и пароль</b> от вашего аккаунта <b>Госуслуг</b>.

🔒 Мы <b>не сохраняем</b> данные для входа. На сервере будет хранится <b>только токен</b>, доступный исключительно <b>Вам</b>. 
Исходный код <b>текущей</b> версии: {get_hash()}

⚙ <b>Запретить доступ</b> в любой сервис можно на https://lk.gosuslugi.ru/settings/safety/events

🔒 Введите <b>логин</b>:
                """,
                disable_web_page_preview=True,
                reply_markup=ReplyKeyboardRemove()
            )
        case "AUPD-TOKEN":
            await state.set_state(Form.token)
            await message.answer(
                "🔒 Введите <b>API-Auth <tg-spoiler>(aupd)</tg-spoiler> токен</b>:",
                reply_markup=ReplyKeyboardRemove(),
            )


async def check_token_send_confirm(message: Message, token: str, state: FSMContext):
    if not token:
        await state.clear()
        await message.answer(
            "⚠️ Кажется, такого аккаунта несуществует / были введены неверные данные / доступ запрещен.\nПожалуйста, зайдите с существующего аккаунта."
        )
        return
    
    api = AsyncMobileAPI(token=token)
    try:
        user_api = await api.get_users_profile_info()
        profile_id = user_api[0].id
        profile = (await api.get_profile(profile_id)).profile

        if profile.type == "student":
            type = "ученик"
        elif profile.type == "parent":
            type = "родитель"
        else:
            await state.clear()
            await message.answer(
                "❔ Неизвестный тип профиля.\nПожалуйста, зайдите с аккаунта родителя или ученика."
            )
            return

        await state.update_data(
            token=token,
            api=api,
            users_profile_info=user_api,
            profile_id=profile_id,
            profile=profile
        )

        await state.set_state(Form.confirm)
        await message.answer(
            (
                f"❔ <b>{profile.last_name} {profile.first_name} {profile.middle_name}, {type}</b>, верно?"
            ),
            reply_markup=YES_OR_NO
        )
    except APIError as e:
        await state.clear()
        await message.answer(
            f"🚫 <b>Произошла ошибка</b>: <code>{e}</code>\nПопробуйте <code>еще раз позднее</code>."
        )


@auth_router.message(Form.token)
async def set_token(message: Message, state: FSMContext):
    token = message.text
    await check_token_send_confirm(message, token, state)


@auth_router.message(Form.username)
async def set_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(Form.password)
    gosuslugi_events = "\n⚙ <b>Запретить доступ</b> в любой сервис можно на https://lk.gosuslugi.ru/settings/safety/events\n" if (await state.get_data())["login_type"] == "gosuslugi" else ""
    await message.answer(
        f"""
✅ <b>Отлично</b>!
Теперь нужно ввести <b>логин и пароль</b> от вашего аккаунта <b>Госуслуг</b>.

🔒 Мы <b>не сохраняем</b> данные для входа. На сервере будет хранится <b>только токен</b>, доступный исключительно <b>Вам</b>. 
Исходный код <b>текущей</b> версии: {get_hash()}
{gosuslugi_events}
🔒 Введите <b>пароль</b>:
        """,
        disable_web_page_preview=True
    )


@auth_router.message(Form.password)
async def set_password(message: Message, state: FSMContext):
    await state.update_data(password=message.text)
    data = await state.get_data()

    api = AsyncMobileAPI()
    try:
        token = (
            await api.esia_login(username=data["username"], password=data["password"])
            if data["login_type"] == "gosuslugi"
            else await api.login(username=data["username"], password=data["password"])
        )
    except APIError as e:
        if e.error_type in ["INVALID_PASSWORD", "authentication_error"]:
            await state.update_data(username=None, password=None)
            await state.set_state(Form.username)
            await message.answer(
                "🚫 Неверный логин или пароль...\n🔒 Введите пожалуйста верный логин:"
            )
        elif e.error_type == "SOLVE_ANOMALY_REACTION":
            await state.clear()
            await message.answer(
                "⚠️ <b>Госуслуги требуют решить капчу</b>!\nПожалуйста, <a href='https://esia.gosuslugi.ru/login/'>зайдите в Госуслуги</a> и решите капчу, затем авторизуйтесь снова.",
                disable_web_page_preview=True
            )
        else:
            await state.clear()
            raise e
    else:
        if token is False:
            await state.update_data(api=api)
            await state.set_state(Form.gosuslugi_mfa)
            await message.answer(
                "🔐 Введите пожалуйста MFA (SMS/TOTP код):"
            )
        else:
            await check_token_send_confirm(message, token, state)
            

@auth_router.message(Form.confirm)
async def confirm(message: Message, state: FSMContext):
    match message.text:
        case "Нет":
            await state.clear()
            await message.answer(
                "Хорошо, тогда авторизуйтесь заново под нужным профилем.",
                reply_markup=ReplyKeyboardRemove()
            )
        case "Да":
            data = await state.get_data()
            user = Database().user(message.from_user.id)
            user.db_users_profile_info = [prof.model_dump() for prof in data["users_profile_info"]]
            user.db_profile_id = data["profile_id"]
            user.db_token = data["token"]
            user.db_system = data["system"]
            user.db_settings = {
                "goals": False,
                "notifications": {
                    "create_mark": True
                }
            }
            user.db_skip_notifications = True
            user.db_notified_ids = []

            await state.clear()

            await message.answer(
                """
✅ <b>Отлично</b>!\nНужные данные были получены, вам теперь доступно расписание, оценки, домашние задания, уведомления и многое другое.

Вы <b>всегда</b> можете в любой момент <b>выйти</b>: /logout
                """,
                reply_markup=DEFAULT if message.chat.type == ChatType.PRIVATE else None
            )
            await on_startup_myschool_router()


@auth_router.message(Form.gosuslugi_mfa)
async def set_gosuslugi_mfa(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(
            "🚫 <b>Неверный</b> код.\nВведите пожалуйста MFA (SMS/TOTP код):"
        )
        return
    
    data = await state.get_data()
    try:
        api: AsyncMobileAPI = data["api"]
        token = await api.esia_enter_MFA(code=int(message.text))
    except APIError as e:
        if e.error_type == "SOLVE_ANOMALY_REACTION":
            await state.clear()
            await message.answer(
                "⚠️ <b>Госуслуги требуют решить капчу</b>!\nПожалуйста, <a href='https://esia.gosuslugi.ru/login/'>зайдите в Госуслуги</a> и решите капчу, затем авторизуйтесь снова.",
                disable_web_page_preview=True
            )
        elif e.error_type in ["INVALID_TTP", "INVALID_OTP"]:
            await state.clear()
            await message.answer(
                "🚫 <b>Неверный</b> код.\nНачните авторизацию <b>заново</b>."
            )
        else:
            await state.clear()
            await message.answer(f"🚫 Произошла <b>ошибка</b>: <code>{e}</code>\n\nНачните авторизацию <b>заново</b>.")
    else:
        await check_token_send_confirm(message, token, state)
