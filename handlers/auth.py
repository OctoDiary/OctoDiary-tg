#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InputMediaPhoto,
    Message,
    ReplyKeyboardRemove,
)

from database import Database
from handlers.myschool._loop import save_my_school_user_data
from handlers.mes._loop import save_mes_user_data
from octodiary.asyncApi.myschool import AsyncMobileAPI as MySchoolMobileAPI
from octodiary.asyncApi.mes import AsyncMobileAPI as MESMobileAPI
from octodiary.exceptions import APIError
from octodiary.types.captcha import Captcha
from octodiary.types.enter_sms_code import EnterSmsCode
from utils.filters import AuthFilter
from utils.keyboard import AUTH_LOGIN_TYPE_MES, AUTH_LOGIN_TYPE_MY_SCHOOL, AUTH_SYSTEMS, DEFAULT, DEFAULT_MES, YES_OR_NO
from utils.other import get_hash, pluralization_string
from utils.texts import Texts

auth_router = Router()

class Form(StatesGroup):
    system = State()
    auth_type = State()

    username = State()
    password = State()
    token = State()

    gosuslugi_mfa = State()
    gosuslugi_captcha = State()
    blitz_otp = State()

    confirm = State()


async def check_token_and_send_confirm(message: Message, token: str, state: FSMContext):
    if not token:
        await state.clear()
        await message.answer(
            Texts.Authorization.INVALID_ACCOUNT,
        )
        return
    
    data = await state.get_data()

    try:
        match data["system"]:
            case Texts.Systems.MES:
                api = MESMobileAPI(token=token)
                user_api = await api.get_users_profiles_info()
                profile_id = user_api[0].id
                profile = (await api.get_family_profile(profile_id)).profile
            case Texts.Systems.MY_SCHOOL:
                api = MySchoolMobileAPI(token=token)
                user_api = await api.get_users_profile_info()
                profile_id = user_api[0].id
                profile = (await api.get_profile(profile_id)).profile

        if profile.type == "student":
            type = Texts.Authorization.TYPE_STUDENT
        elif profile.type == "parent":
            type = Texts.Authorization.TYPE_PARENT
        else:
            await state.clear()
            await message.answer(text=Texts.Authorization.UNKNOWN_ACCOUNT_TYPE)
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
            text=Texts.Authorization.CONFIRM(profile=profile, type=type),
            reply_markup=YES_OR_NO
        )
    except APIError as e:
        await state.clear()
        await message.answer(text=Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))


@auth_router.message(Command(commands=["auth", "login"]))
async def auth(message: Message, state: FSMContext):
    if Database().user(str(message.from_user.id)).token:
        await message.answer(Texts.Authorization.ALREADY_AUTHORIZED)
        return

    await state.set_state(Form.system)
    await message.answer(
        Texts.Authorization.SELECT_SYSTEM,
        reply_markup=AUTH_SYSTEMS,
        resize_keyboard=True
    )


@auth_router.message(Form.system, AuthFilter())
async def set_system(message: Message, state: FSMContext):
    match message.text:
        case Texts.MES:
            await state.update_data(
                system=Texts.Systems.MES
            )
            await state.set_state(Form.auth_type)
            await message.answer(
                Texts.Authorization.SELECT_LOGIN_TYPE,
                reply_markup=AUTH_LOGIN_TYPE_MES
            )
            
        case Texts.MY_SCHOOL:
            await state.update_data(
                system=Texts.Systems.MY_SCHOOL
            )
            await state.set_state(Form.auth_type)
            await message.answer(
                Texts.Authorization.SELECT_LOGIN_TYPE,
                reply_markup=AUTH_LOGIN_TYPE_MY_SCHOOL
            )


@auth_router.message(Form.auth_type, AuthFilter())
async def set_login_type(message: Message, state: FSMContext):
    match message.text:
        case Texts.LoginAndPassword:
            await state.update_data(login_type=Texts.LoginTypes.LoginAndPassword)
            await state.set_state(Form.username)
            await message.answer(
                (
                    Texts.Authorization.MY_SCHOOL_ENTER_USERNAME
                    if (await state.get_data()).get("system") == Texts.Systems.MY_SCHOOL
                    else Texts.Authorization.MES_ENTER_USERNAME
                )(
                    HASH=get_hash()
                ),
                disable_web_page_preview=True,
                reply_markup=ReplyKeyboardRemove()
            )
        case Texts.Gosuslugi:
            if (await state.get_data()).get("system") == Texts.Systems.MES:
                await state.clear()
                await message.answer(
                    Texts.Authorization.NOT_SUPPORTED,
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            await state.update_data(login_type=Texts.LoginTypes.Gosuslugi)
            await state.set_state(Form.username)
            await message.answer(
                Texts.Authorization.GOSUSLUGI_ENTER_USERNAME(
                    HASH=get_hash()
                ),
                disable_web_page_preview=True,
                reply_markup=ReplyKeyboardRemove()
            )
        case Texts.AUPD_TOKEN:
            await state.set_state(Form.token)
            await message.answer(
                Texts.Authorization.ENTER_TOKEN,
                reply_markup=ReplyKeyboardRemove(),
            )


@auth_router.message(Form.token, AuthFilter())
async def set_token(message: Message, state: FSMContext):
    token = message.text
    await check_token_and_send_confirm(message, token, state)


@auth_router.message(Form.username)
async def set_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(Form.password)
    data = await state.get_data()
    await message.answer(
        (
            Texts.Authorization.GOSUSLUGI_ENTER_PASSWORD
            if data["login_type"] == Texts.LoginTypes.Gosuslugi
            else Texts.Authorization.MY_SCHOOL_ENTER_PASSWORD
            if data["system"] == Texts.Systems.MY_SCHOOL
            else Texts.Authorization.MES_ENTER_PASSWORD
        )(HASH=get_hash()),
        disable_web_page_preview=True
    )


async def renew_captcha(call: CallbackQuery, captcha: Captcha, bot: Bot, last_voice: Message | None = None):
    await captcha.async_renew_image_captcha()
    if last_voice:
        await last_voice.delete()
    await bot.edit_message_media(
        media=InputMediaPhoto(
            media=BufferedInputFile(
                file=captcha.image_bytes,
                filename=Texts.Variables.CAPTCHA_IMAGE_FILENAME
            ),
            caption=Texts.Authorization.ENTER_SYMBOLS_FROM_IMAGE
        ),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=bot.inline.generate_markup(
            [
                [
                    {
                        "text": Texts.Authorization.DIFFERENT_CODE,
                        "callback": renew_captcha,
                        "kwargs": {
                            "captcha": captcha,
                            "bot": bot
                        }
                    }
                ],
                [
                    {
                        "text": Texts.Authorization.RECORD_VOICE,
                        "callback": voice_captcha,
                        "kwargs": {
                            "captcha": captcha,
                            "bot": bot
                        }
                    }
                ]
            ]
        )
    )
    await call.answer(text=Texts.SUCCESSFULLY)


async def voice_captcha(call: CallbackQuery, captcha: Captcha, bot: Bot):
    voice_bytes = await captcha.async_get_voice()
    voice_message = await bot.send_voice(
        chat_id=call.message.chat.id,
        voice=BufferedInputFile(file=voice_bytes, filename=Texts.Variables.CAPTCHA_VOICE_FILENAME),
        caption=Texts.Authorization.VOICE,
        reply_to_message_id=call.message.message_id
    )
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=bot.inline.generate_markup(
            [
                [
                    {
                        "text": Texts.Authorization.DIFFERENT_CODE,
                        "callback": renew_captcha,
                        "kwargs": {
                            "captcha": captcha,
                            "bot": bot,
                            "latest_voice": voice_message
                        }
                    }
                ]
            ]
        )
    )
    await call.answer(text=Texts.SUCCESSFULLY)


@auth_router.message(Form.password)
async def set_password(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(password=message.text)
    data = await state.get_data()

    match data["system"]:
        case Texts.Systems.MY_SCHOOL:
            api = MySchoolMobileAPI()
            try:
                response = (
                    await api.esia_login(username=data["username"], password=data["password"])
                    if data["login_type"] == Texts.LoginTypes.Gosuslugi
                    else await api.login(username=data["username"], password=data["password"])
                )
            except APIError as e:
                if e.error_type in ["INVALID_PASSWORD", "authentication_error"]:
                    await state.update_data(username=None, password=None)
                    await state.set_state(Form.username)
                    await message.answer(
                        Texts.Authorization.INVALID_PASSWORD
                    )
                else:
                    await state.clear()
                    raise e
            else:
                if isinstance(response, Captcha):
                    await state.update_data(api=api)
                    await state.update_data(captcha=response)
                    await state.set_state(Form.gosuslugi_captcha)
                    if response.question:
                        await message.answer(text=Texts.Authorization.RESOLVE_CAPTCHA(QUESTION=response.question))
                    else:
                        await message.answer_photo(
                            photo=BufferedInputFile(response.image_bytes, Texts.Variables.CAPTCHA_IMAGE_FILENAME),
                            caption=Texts.Authorization.ENTER_SYMBOLS_FROM_IMAGE,
                            reply_markup=bot.inline.generate_markup(
                                [
                                    [
                                        {
                                            "text": Texts.Authorization.DIFFERENT_CODE,
                                            "callback": renew_captcha,
                                            "kwargs": {
                                                "captcha": response,
                                                "bot": bot
                                            }
                                        }
                                    ],
                                    [
                                        {
                                            "text": Texts.Authorization.RECORD_VOICE,
                                            "callback": voice_captcha,
                                            "kwargs": {
                                                "captcha": response,
                                                "bot": bot
                                            }
                                        }
                                    ]
                                ]
                            )
                        )
                elif response is False:
                    await state.update_data(api=api)
                    await state.set_state(Form.gosuslugi_mfa)
                    mfa_method = api._mfa_details["type"]
                    if mfa_method == "SMS":
                        phone = api._mfa_details["otp_details"]["phone"]
                        await message.answer(
                            text=Texts.Authorization.MFA_ENTER_OTP(PHONE=phone),
                            parse_mode="HTML"
                        )
                    else:
                        await message.answer(text=Texts.Authorization.MFA_ENTER_TTP)
                else:
                    await check_token_and_send_confirm(message, response, state)
        case Texts.Systems.MES:
            api = MESMobileAPI()
            try:
                response = await api.login(username=data["username"], password=data["password"])
            except APIError as e:
                match e.error_type:
                    case "InvalidCredentials":
                        await state.update_data(username=None, password=None)
                        await state.set_state(Form.username)
                        await message.answer(
                            Texts.Authorization.INVALID_PASSWORD
                        )
                        return
                    case "TemporarilyBlocked":
                        await state.clear()
                        await message.answer(
                            text=Texts.Authorization.TEMPORARY_BLOCKED
                        )
                        return
                    case "NotFound":
                        await state.clear()
                        await message.answer(
                            text=Texts.Authorization.NOT_FOUND
                        )
                        return
                    case _:
                        raise e
            else:
                if isinstance(response, EnterSmsCode):
                    await state.update_data(api=api, enter_code=response)
                    await state.set_state(Form.blitz_otp)
                    phone = "+" + response.contact[0:4] + "*****" + response.contact[-2:]
                    await message.answer(
                        text=Texts.Authorization.BLITZ_SEND_CODE(PHONE=phone),
                        parse_mode="HTML"
                    )
                else:
                    await check_token_and_send_confirm(message, response, state)


@auth_router.message(Form.gosuslugi_mfa)
async def set_gosuslugi_mfa(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit() or len(message.text) != 6:
        await message.answer(text=Texts.Authorization.INVALID_MFA_ENTER_AGAIN)
        return

    data = await state.get_data()
    try:
        api: MySchoolMobileAPI = data["api"]
        response = await api.esia_enter_MFA(code=int(message.text))
    except APIError as e:
        if e.error_type in ["INVALID_TTP", "INVALID_OTP"]:
            await state.clear()
            await message.answer(text=Texts.Authorization.INVALID_MFA)
        else:
            await state.clear()
            await message.answer(Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))
    else:
        if isinstance(response, Captcha):
            await state.update_data(captcha=response)
            await state.set_state(Form.gosuslugi_captcha)
            if response.question:
                await message.answer(text=Texts.Authorization.RESOLVE_CAPTCHA(QUESTION=response.question))
            else:
                await message.answer_photo(
                    photo=BufferedInputFile(response.image_bytes, Texts.Variables.CAPTCHA_IMAGE_FILENAME),
                    caption=Texts.Authorization.ENTER_SYMBOLS_FROM_IMAGE,
                    reply_markup=bot.inline.generate_markup(
                        [
                            [
                                {
                                    "text": Texts.Authorization.DIFFERENT_CODE,
                                    "callback": renew_captcha,
                                    "kwargs": {
                                        "captcha": response,
                                        "bot": bot
                                    }
                                }
                            ],
                            [
                                {
                                    "text": Texts.Authorization.RECORD_VOICE,
                                    "callback": voice_captcha,
                                    "kwargs": {
                                        "captcha": response,
                                        "bot": bot
                                    }
                                }
                            ]
                        ]
                    )
                )
        else:
            await check_token_and_send_confirm(message, response, state)


@auth_router.message(Form.gosuslugi_captcha)
async def asnwer_gosuslugi_captcha(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    captcha: Captcha = data["captcha"]

    try:
        response = await (
            captcha.async_asnwer_captcha
            if captcha.question
            else captcha.async_verify_captcha
        )(message.text)
    except APIError as e:
        if e.error_type == "INVALID_PASSWORD":
            await state.update_data(username=None, password=None)
            await state.set_state(Form.username)
            await message.answer(
                Texts.Authorization.INVALID_PASSWORD
            )
        else:
            await state.clear()
            await message.answer(Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))
    else:
        if isinstance(response, Captcha):
            await state.update_data(captcha=response)
            if response.question:
                await message.answer(text=Texts.Authorization.RESOLVE_CAPTCHA(QUESTION=response.question))
            else:
                await message.answer_photo(
                    photo=BufferedInputFile(response.image_bytes, Texts.Variables.CAPTCHA_IMAGE_FILENAME),
                    caption=Texts.Authorization.ENTER_SYMBOLS_FROM_IMAGE,
                    reply_markup=bot.inline.generate_markup(
                        [
                            [
                                {
                                    "text": Texts.Authorization.DIFFERENT_CODE,
                                    "callback": renew_captcha,
                                    "kwargs": {
                                        "captcha": response,
                                        "bot": bot
                                    }
                                }
                            ],
                            [
                                {
                                    "text": Texts.Authorization.RECORD_VOICE,
                                    "callback": voice_captcha,
                                    "kwargs": {
                                        "captcha": response,
                                        "bot": bot
                                    }
                                }
                            ]
                        ]
                    )
                )
        elif response is False:
            api = data["api"]
            await state.set_state(Form.gosuslugi_mfa)
            mfa_method = api._mfa_details["type"]
            if mfa_method == "SMS":
                phone = api._mfa_details["otp_details"]["phone"]
                await message.answer(
                    text=Texts.Authorization.MFA_ENTER_OTP(PHONE=phone),
                    parse_mode="HTML"
                )
            else:
                await message.answer(text=Texts.Authorization.MFA_ENTER_TTP)
        else:
            await check_token_and_send_confirm(message, response, state)


@auth_router.message(Form.blitz_otp)
async def set_blitz_otp(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit() or len(message.text) != 6:
        await message.answer(text=Texts.Authorization.INVALID_MFA_ENTER_AGAIN)
        return
    
    data = await state.get_data()
    enter_code: EnterSmsCode = data["enter_code"]

    try:
        response = await enter_code.async_enter_code(message.text)
    except APIError as e:
        match e.error_type:
            case "InvalidOTP":
                await message.answer(text=Texts.Authorization.BLITZ_INVALID_CODE(
                    ATTEMPTS=pluralization_string(e.details["remain_attempts"], ["попытка", "попытки", "попыток"]),
                    TTL=pluralization_string(e.details["ttl"], ["секунда", "секунды", "секунд"])
                ))
            case "NoAttempts" | "CodeExpired":
                await message.answer(text=Texts.Authorization.BLITZ_CODE_EXPIRED)
            case _:
                await state.clear()
                await message.answer(text=Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))
                raise e
    else:
        print(response)
        await check_token_and_send_confirm(message, response, state)


@auth_router.message(Form.confirm)
async def confirm(message: Message, state: FSMContext):
    match message.text:
        case Texts.NO:
            await state.clear()
            await message.answer(
                text=Texts.Authorization.NOT_CONFIRM,
                reply_markup=ReplyKeyboardRemove()
            )
        case Texts.YES:
            data = await state.get_data()
            db = Database()
            user = db.user(str(message.from_user.id))
            db.settings.set(
                "users",
                list({*db.settings.get("users", []), message.from_user.id})
            )
            db.settings.set(
                f"new-users-month:{date.today().month}",
                db.settings.get(f"new-users-month:{date.today().month}", 0) + 1
            )
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
            
            if data["system"] == Texts.Systems.MY_SCHOOL:
                await save_my_school_user_data(str(message.from_user.id))
            else:
                await save_mes_user_data(str(message.from_user.id))

            await state.clear()

            await message.answer(
                text=Texts.Authorization.SUCCESS_CONFIRM,
                reply_markup=(
                    (
                        DEFAULT
                        if data["system"] == Texts.Systems.MY_SCHOOL
                        else DEFAULT_MES
                    )
                    if message.chat.type == ChatType.PRIVATE
                    else None
                )
            )
