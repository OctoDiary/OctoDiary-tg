#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import re
from contextlib import suppress

import requests
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
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
from handlers.loop import save_user_data
from octodiary.apis import AsyncMobileAPI
from octodiary.exceptions import APIError
from octodiary.types.captcha import Captcha
from octodiary.types.enter_sms_code import EnterSmsCode
from utils.filters import AuthFilter
from utils.keyboard import (
    AUTH_LOGIN_TYPE_MES,
    AUTH_LOGIN_TYPE_MY_SCHOOL,
    AUTH_SYSTEMS,
    CANCEL,
    DEFAULT,
    DEFAULT_MES,
    YES_OR_NO,
)
from utils.other import ODAuth, get_date, get_hash, pluralization_string
from utils.texts import Texts

auth_router = Router()


class Authorization(StatesGroup):
    system = State()
    auth_type = State()

    username = State()
    password = State()
    token = State()

    gosuslugi_mfa = State()
    gosuslugi_captcha = State()
    blitz_otp = State()

    confirm = State()


@auth_router.message(Command("cancel"))
@auth_router.message(F.text == Texts.Buttons.CANCEL)
async def cancel(message: Message, state: FSMContext):
    if not (state_name := await state.get_state()):
        return

    await state.clear()
    await message.answer(
        text=getattr(Texts, state_name.split(":")[0]).CANCEL,
        reply_markup=ReplyKeyboardRemove()
    )


async def check_token_and_send_confirm(message: Message, token: str, state: FSMContext):
    if not token:
        await state.clear()
        await message.edit_text(
            Texts.Authorization.INVALID_ACCOUNT,
        )
        return

    data = await state.get_data()

    try:
        api = AsyncMobileAPI(system=data["system"], token=token)
        user_api = await api.get_users_profile_info()
        profile_id = user_api[0].id
        profile = (await api.get_family_profile(profile_id)).profile

        match profile.type:
            case "student":
                user_type = Texts.Authorization.TYPE_STUDENT
            case "parent":
                user_type = Texts.Authorization.TYPE_PARENT
            case _:
                await state.clear()
                await message.edit_text(text=Texts.Authorization.UNKNOWN_ACCOUNT_TYPE)
                return

        await state.update_data(
            token=token,
            api=api,
            users_profile_info=user_api,
            profile_id=profile_id,
            profile=profile
        )

        await state.set_state(Authorization.confirm)
        await message.answer(
            text=Texts.Authorization.CONFIRM(profile=profile, type=user_type),
            reply_markup=YES_OR_NO
        )
        await message.delete()
    except APIError as e:
        await state.clear()
        await message.answer(text=Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))


@auth_router.message(Command(commands=["auth", "login", "reauth"]))
async def auth(message: Message, state: FSMContext, command: CommandObject):
    if command.command == "reauth":
        with suppress(Exception):
            Database().pop(str(message.from_user.id))
    elif Database().user(str(message.from_user.id)).token:
        await message.answer(Texts.Authorization.ALREADY_AUTHORIZED)
        return

    await state.set_state(Authorization.system)
    await message.answer(
        Texts.Authorization.SELECT_SYSTEM,
        reply_markup=AUTH_SYSTEMS,
        resize_keyboard=True
    )


@auth_router.message(Authorization.system, AuthFilter())
async def set_system(message: Message, state: FSMContext):
    if message.text == Texts.MES:
        system = Texts.Systems.MES
        reply_markup = AUTH_LOGIN_TYPE_MES
    elif message.text == Texts.MY_SCHOOL:
        system = Texts.Systems.MY_SCHOOL
        reply_markup = AUTH_LOGIN_TYPE_MY_SCHOOL
    else:
        return

    await state.update_data(
        system=system
    )

    await state.set_state(Authorization.auth_type)
    await message.answer(
        Texts.Authorization.SELECT_LOGIN_TYPE,
        reply_markup=reply_markup
    )


@auth_router.message(Authorization.auth_type, AuthFilter())
async def set_login_type(message: Message, state: FSMContext):
    match message.text:
        case Texts.LoginAndPassword | Texts.MosRu:
            await state.update_data(login_type=Texts.LoginTypes.LoginAndPassword)
            await state.set_state(Authorization.username)
            await message.answer(
                (
                    Texts.Authorization.MY_SCHOOL_ENTER_USERNAME
                    if (await state.get_data()).get("system") == Texts.Systems.MY_SCHOOL
                    else Texts.Authorization.MES_ENTER_USERNAME
                )(
                    HASH=get_hash()
                ),
                disable_web_page_preview=True,
                reply_markup=CANCEL
            )
        case Texts.Gosuslugi:
            if (await state.get_data()).get("system") == Texts.Systems.MES:
                await state.clear()
                await message.answer(
                    Texts.Authorization.NOT_SUPPORTED,
                    reply_markup=CANCEL
                )
                return

            await state.update_data(login_type=Texts.LoginTypes.Gosuslugi)
            await state.set_state(Authorization.username)
            await message.answer(
                Texts.Authorization.GOSUSLUGI_ENTER_USERNAME(
                    HASH=get_hash()
                ),
                disable_web_page_preview=True,
                reply_markup=CANCEL
            )
        case Texts.AUPD_TOKEN:
            if (await state.get_data()).get("system") == Texts.Systems.MES:
                await state.clear()
                await message.answer(
                    Texts.Authorization.NOT_SUPPORTED,
                    reply_markup=CANCEL
                )
                return

            await state.update_data(login_type=Texts.LoginTypes.AUPD_TOKEN)
            await state.set_state(Authorization.token)
            await message.answer(
                Texts.Authorization.ENTER_TOKEN(system="МЭШ" if (await state.get_data()).get("system") == Texts.Systems.MES else "Моей Школы"),
                reply_markup=CANCEL
            )


@auth_router.message(Authorization.token, AuthFilter())
async def set_token(message: Message, state: FSMContext):
    response = await message.answer(Texts.LOADING, reply_markup=CANCEL)

    await check_token_and_send_confirm(response, token=message.text, state=state)


@auth_router.message(Authorization.username)
async def set_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(Authorization.password)
    data = await state.get_data()
    await message.answer(
        (
            Texts.Authorization.GOSUSLUGI_ENTER_PASSWORD
            if data["login_type"] == Texts.LoginTypes.Gosuslugi
            else Texts.Authorization.MY_SCHOOL_ENTER_PASSWORD
            if data["system"] == Texts.Systems.MY_SCHOOL
            else Texts.Authorization.MES_ENTER_PASSWORD
        )(HASH=get_hash()),
        disable_web_page_preview=True,
        reply_markup=CANCEL
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


async def send_captcha(
        response: Captcha,
        message: Message,
        bot: Bot
):
    if response.question:
        await message.answer(text=Texts.Authorization.RESOLVE_CAPTCHA(QUESTION=response.question), reply_markup=CANCEL)
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


async def send_mfa_user_request(
        api: AsyncMobileAPI,
        message: Message
):
    mfa_method = api._mfa_details["type"]
    if mfa_method == "SMS":
        phone = api._mfa_details["otp_details"]["phone"]
        await message.answer(
            text=Texts.Authorization.MFA_ENTER_OTP(PHONE=phone),
            parse_mode="HTML",
            reply_markup=CANCEL
        )
    else:
        await message.answer(text=Texts.Authorization.MFA_ENTER_TTP, reply_markup=CANCEL)


@auth_router.message(Authorization.password)
async def set_password(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(password=message.text)
    data = await state.get_data()

    match data["system"]:
        case Texts.Systems.MY_SCHOOL:
            api = AsyncMobileAPI(system=Texts.Systems.MY_SCHOOL)
            try:
                response = (
                    await api.esia_login(username=data["username"], password=data["password"])
                    if data["login_type"] == Texts.LoginTypes.Gosuslugi
                    else await api.login(username=data["username"], password=data["password"])
                )
            except APIError as e:
                if any(i == e.error_types for i in ["INVALID_PASSWORD", "authentication_error"]):
                    await state.update_data(username=None, password=None)
                    await state.set_state(Authorization.username)
                    await message.answer(
                        Texts.Authorization.INVALID_PASSWORD, reply_markup=CANCEL
                    )
                else:
                    await state.clear()
                    raise e
            else:
                if isinstance(response, Captcha):
                    await state.update_data(api=api, captcha=response)
                    await state.set_state(Authorization.gosuslugi_captcha)
                    await send_captcha(response=response, message=message, bot=bot)
                elif response is False:
                    await state.update_data(api=api)
                    await state.set_state(Authorization.gosuslugi_mfa)
                    await send_mfa_user_request(api=api, message=message)
                else:
                    response_msg = await message.answer(Texts.LOADING, reply_markup=CANCEL)
                    await check_token_and_send_confirm(response_msg, response, state)
        case Texts.Systems.MES:
            api = AsyncMobileAPI(system=Texts.Systems.MES)
            await state.update_data(auth_api=api)
            try:
                response = await api.login(username=data["username"], password=data["password"])
            except APIError as e:
                match e.error_types:
                    case "InvalidCredentials":
                        await state.update_data(username=None, password=None)
                        await state.set_state(Authorization.username)
                        await message.answer(
                            Texts.Authorization.INVALID_PASSWORD, reply_markup=CANCEL
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
                    await state.set_state(Authorization.blitz_otp)
                    phone = "+" + response.contact[0:4] + "*****" + response.contact[-2:]
                    await message.answer(
                        text=Texts.Authorization.BLITZ_SEND_CODE(PHONE=phone),
                        parse_mode="HTML", reply_markup=CANCEL
                    )
                else:
                    response_msg = await message.answer(Texts.LOADING, reply_markup=CANCEL)
                    await check_token_and_send_confirm(response_msg, response, state)


@auth_router.message(Authorization.gosuslugi_mfa)
async def set_gosuslugi_mfa(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit() or len(message.text) != 6:
        await message.answer(text=Texts.Authorization.INVALID_MFA_ENTER_AGAIN, reply_markup=CANCEL)
        return

    data = await state.get_data()
    try:
        api: AsyncMobileAPI = data["api"]
        response = await api.esia_enter_MFA(code=int(message.text))
    except APIError as e:
        if e.error_types in ["INVALID_TTP", "INVALID_OTP"]:
            await state.clear()
            await message.answer(text=Texts.Authorization.INVALID_MFA)
        else:
            await state.clear()
            await message.answer(Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))
    else:
        if isinstance(response, Captcha):
            await state.update_data(captcha=response)
            await state.set_state(Authorization.gosuslugi_captcha)
            await send_captcha(response=response, message=message, bot=bot)
        else:
            response_msg = await message.answer(Texts.LOADING, reply_markup=CANCEL)
            await check_token_and_send_confirm(response_msg, response, state)


@auth_router.message(Authorization.gosuslugi_captcha)
async def answer_gosuslugi_captcha(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    captcha: Captcha = data["captcha"]

    try:
        response = await (
            captcha.async_asnwer_captcha
            if captcha.question
            else captcha.async_verify_captcha
        )(message.text)
    except APIError as e:
        if e.error_types == "INVALID_PASSWORD":
            await state.update_data(username=None, password=None)
            await state.set_state(Authorization.username)
            await message.answer(
                Texts.Authorization.INVALID_PASSWORD, reply_markup=CANCEL
            )
        else:
            await state.clear()
            await message.answer(Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))
    else:
        if isinstance(response, Captcha):
            await state.update_data(captcha=response)
            await send_captcha(response=response, message=message, bot=bot)
        elif response is False:
            api = data["api"]
            await state.set_state(Authorization.gosuslugi_mfa)
            await send_mfa_user_request(api=api, message=message)
        else:
            response_msg = await message.answer(Texts.LOADING, reply_markup=CANCEL)
            await check_token_and_send_confirm(response_msg, response, state)


@auth_router.message(Authorization.blitz_otp)
async def set_blitz_otp(message: Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 6:
        await message.answer(text=Texts.Authorization.INVALID_MFA_ENTER_AGAIN, reply_markup=CANCEL)
        return

    data = await state.get_data()
    enter_code: EnterSmsCode = data["enter_code"]

    try:
        response: str = await enter_code.async_enter_code(message.text)
    except APIError as e:
        match e.error_types:
            case "InvalidOTP":
                await message.answer(text=Texts.Authorization.BLITZ_INVALID_CODE(
                    ATTEMPTS=pluralization_string(e.details["remain_attempts"], ["попытка", "попытки", "попыток"]),
                    TTL=pluralization_string(e.details["ttl"], ["секунда", "секунды", "секунд"]),
                    reply_markup=CANCEL
                ))
            case "NoAttempts" | "CodeExpired":
                await message.answer(text=Texts.Authorization.BLITZ_CODE_EXPIRED, reply_markup=CANCEL)
            case _:
                await state.clear()
                await message.answer(text=Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))
                raise e
    else:
        response_msg = await message.answer(Texts.LOADING, reply_markup=CANCEL)
        await check_token_and_send_confirm(response_msg, response, state)


@auth_router.message(Authorization.confirm)
async def confirm(message: Message, state: FSMContext):
    match message.text:
        case Texts.NO:
            await state.clear()
            await message.answer(
                text=Texts.Authorization.NOT_CONFIRM,
                reply_markup=CANCEL
            )
        case Texts.YES:
            response = await message.answer(Texts.LOADING, reply_markup=CANCEL)
            data = await state.get_data()
            db = Database()
            user = db.user(str(message.from_user.id))
            db.settings.set(
                "users",
                list({*db.settings.get("users", []), message.from_user.id})
            )
            db.settings.set(
                f"new-users-month:{get_date().month}",
                db.settings.get(f"new-users-month:{get_date().month}", 0) + 1
            )
            user.db_users_profile_info = [prof.model_dump() for prof in data["users_profile_info"]]
            user.db_profile_id = data["profile_id"]
            user.db_token = data["token"]
            user.db_system = data["system"]

            if data["system"] == Texts.Systems.MES:
                if "auth_api" in data:
                    od_auth_settings = ODAuth(
                        access_token=data["token"],
                        refresh_token=data["auth_api"].token_for_refresh,
                        client_id=data["auth_api"].client_id,
                        client_secret=data["auth_api"].client_secret
                    )
                    await data["api"].edit_user_settings_app(od_auth_settings, name="od_auth", profile_id=data["profile_id"])
                else:
                    od_auth_settings = await data["api"].get_user_settings_app(
                        name="od_auth",
                        profile_id=data["profile_id"],
                        settings_model=ODAuth
                    )

                user.db_od_auth = od_auth_settings.model_dump(mode="json")

            user.db_settings = {
                "goals": False,
                "notifications": {
                    "create_mark": True
                }
            }
            user.db_skip_notifications = True

            await save_user_data(str(message.from_user.id), bot=message.bot)

            await state.clear()

            await response.answer(
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
            await response.delete()


async def app_auth(message: Message, state: FSMContext, match: re.Match):
    token_hex = match.group(1)

    info: dict[str, str] = requests.get("https://octodiary.dsop.online/token_info?token_hex=" + token_hex, timeout=10).json()

    await state.update_data(
        token=info["token"],
        system=info["system"]
    )

    response = await message.answer(Texts.LOADING, reply_markup=CANCEL)

    await check_token_and_send_confirm(response, token=info["token"], state=state)
