#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import re
import typing
from contextlib import suppress

import jwt
import requests
from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, \
    BufferedInputFile, InputMediaPhoto, ReactionTypeEmoji
from octodiary.apis import AsyncMobileAPI
from octodiary.exceptions import APIError
from octodiary.types.captcha import Captcha
from octodiary.types.enter_sms_code import EnterSmsCode

from core.keyboards.inline import SYSTEMS, LOGIN_METHODS_MY_SCHOOL, CONFIRM
from core.keyboards.reply import root_menu
from core.misc.states import Authorization
from core.misc.texts import Texts
from core.misc.utils import pluralization_string, get_date
from core.services.api import UserData
from core.services.database import database

router = Router(name="auth")


async def check_data(
    msg: Message,
    token: typing.Optional[str] = None,
    *,
    state: FSMContext,
    bot: Bot
):
    data = await state.get_data()

    if not token:
        match data.get("login_type") or data.get("system"):
            case "MES" | "mes":
                api = AsyncMobileAPI(system=Texts.Systems.MES)
                await state.update_data(auth_api=api)
                try:
                    response = await api.login(username=data["username"], password=data["password"])
                except APIError as e:
                    match e.error_types:
                        case "InvalidCredentials":
                            await state.update_data(username=None, password=None)
                            await state.set_state(Authorization.username)
                            await msg.edit_text(
                                Texts.Authorization.INVALID_PASSWORD
                            )
                            return
                        case "TemporarilyBlocked":
                            await state.clear()
                            await msg.edit_text(
                                text=Texts.Authorization.TEMPORARY_BLOCKED
                            )
                            return
                        case "NotFound":
                            await state.clear()
                            await msg.edit_text(
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
                        await msg.edit_text(
                            text=Texts.Authorization.BLITZ_SEND_CODE(PHONE=phone),
                            parse_mode="HTML"
                        )
                    else:
                        response_msg = await msg.edit_text(Texts.LOADING)
                        return await check_data(response_msg, response, state=state, bot=bot)
            case "logpass" | "gosuslugi":
                api = AsyncMobileAPI(system=Texts.Systems.MY_SCHOOL)
                try:
                    response = (
                        await api.esia_login(username=data["username"], password=data["password"])
                        if data["login_type"] == "gosuslugi"
                        else await api.login(username=data["username"], password=data["password"])
                    )
                except APIError as e:
                    if any(i == e.error_types for i in ["INVALID_PASSWORD", "authentication_error"]):
                        await state.update_data(username=None, password=None)
                        await state.set_state(Authorization.username)
                        await msg.edit_text(
                            Texts.Authorization.INVALID_PASSWORD
                        )
                    else:
                        await state.clear()
                        raise e
                else:
                    if isinstance(response, Captcha):
                        await state.update_data(api=api, captcha=response)
                        await state.set_state(Authorization.gosuslugi_captcha)
                        await send_captcha(response=response, message=msg, bot=bot)
                    elif response is False:
                        await state.update_data(api=api)
                        await state.set_state(Authorization.gosuslugi_mfa)
                        await send_mfa_user_request(api=api, message=msg)
                    else:
                        return await check_data(msg, response, state=state, bot=bot)
    else:
        try:
            api = AsyncMobileAPI(system=data["system"].lower().replace("_", ""), token=token)
            user_api = await api.get_users_profile_info()
            profile_id = user_api[0].id
            profile = (await api.get_family_profile(profile_id)).profile

            match profile.type:
                case "student" | None:
                    user_type = Texts.Authorization.TYPE_STUDENT
                case "parent":
                    user_type = Texts.Authorization.TYPE_PARENT
                case _:
                    await state.clear()
                    await msg.edit_text(text=Texts.Authorization.UNKNOWN_ACCOUNT_TYPE)
                    return

            await state.update_data(
                token=token,
                api=api,
                users_profile_info=user_api,
                profile_id=profile_id,
                profile=profile
            )

            await state.set_state(Authorization.confirm)
            await msg.edit_text(
                text=Texts.Authorization.CONFIRM(profile=profile, type=user_type),
                reply_markup=CONFIRM
            )
        except APIError as e:
            await state.clear()
            await msg.edit_text(
                text=Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e))
            )


@router.message(Command(commands=["auth", "login", "reauth"]), F.chat.type == ChatType.PRIVATE)
async def auth(message: Message, state: FSMContext, command: CommandObject):
    if command.command == "reauth":
        with suppress(Exception):
            database.pop(str(message.from_user.id))
    elif database.user(str(message.from_user.id)).token:
        await message.answer(Texts.Authorization.ALREADY_AUTHORIZED)
        return

    await state.set_state(Authorization.system)
    await message.answer(
        Texts.Authorization.SELECT_SYSTEM,
        reply_markup=SYSTEMS,
        resize_keyboard=True
    )


@router.callback_query(Authorization.system, F.data.in_(Texts.SystemsNames.keys()))
async def set_system(call: CallbackQuery, state: FSMContext, back: bool = False):
    if not back:
        await state.update_data(system=call.data)

    system = (await state.get_data())["system"]
    await state.set_state(Authorization.method)

    await call.message.edit_text(
        Texts.Authorization.AUTH_METHODS(
            domain="dnevnik.mos.ru" if system == "mes" else "myschool.mosreg.ru",
            system=getattr(Texts.SystemsNames, system)
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=Texts.Buttons.AUTH_METHOD_WEB,
                        callback_data="web"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=Texts.Buttons.AUTH_METHOD_TOKEN,
                        callback_data="token"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=Texts.Buttons.AUTH_METHOD_MANUAL,
                        callback_data="manual"
                    )
                ]
            ]
        )
    )


@router.callback_query(Authorization.method, F.data.in_(["web", "token", "manual"]))
async def auth_method(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data(method=call.data)
    data = await state.get_data()

    match call.data:
        case "web":
            await state.set_state(Authorization.web)

            await call.message.edit_text(
                Texts.Authorization.AUTH_WEB_INFO(
                    domain="dnevnik.mos.ru" if data["system"] == "mes" else "myschool.mosreg.ru",
                    system=getattr(Texts.SystemsNames, data["system"]),
                    METHOD="Автоматически (рекомендуется)",
                    BLOCKQUOTE=(
                        Texts.Authorization.MES_WEB_INFO
                        if data["system"] == "mes"
                        else Texts.Authorization.MY_SCHOOL_WEB_INFO
                    )
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.AUTH_WEB,
                                url=Texts.Authorization.WEB_AUTH_URL_MES(user_id=call.from_user.id)
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.AUTH_TG_WEB_APP,
                                web_app=WebAppInfo(
                                    url=Texts.Authorization.WEB_AUTH_URL_MES(user_id=call.from_user.id)
                                )
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.BACK,
                                callback_data="back"
                            )
                        ]
                    ] if data["system"] == "mes" else [
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.AUTH_WEB_GOSUSLUGI,
                                url=Texts.Authorization.WEB_AUTH_URL_MS(user_id=call.from_user.id)
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.AUTH_WEB_LOGPASS,
                                web_app=WebAppInfo(
                                    url=Texts.Authorization.WEB_AUTH_URL_MS_LOGPASS(user_id=call.from_user.id)
                                )
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.BACK,
                                callback_data="back"
                            )
                        ]
                    ]
                )
            )
        case "token":
            await state.set_state(Authorization.token)
            await call.message.edit_text(
                Texts.Authorization.AUTH_TOKEN_INFO(
                    domain="dnevnik.mos.ru" if data["system"] == "mes" else "myschool.mosreg.ru",
                    system=getattr(Texts.SystemsNames, data["system"]),
                    METHOD="Вход по токену доступа"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.AUTH_GET_TOKEN,
                                url=(
                                    Texts.Authorization.GET_TOKEN_URL_MES
                                    if data["system"] == "mes"
                                    else Texts.Authorization.GET_TOKEN_URL_MY_SCHOOL
                                )
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=Texts.Buttons.BACK,
                                callback_data="back"
                            )
                        ]
                    ]
                )
            )
            await call.message.answer(
                Texts.Authorization.ENTER_TOKEN(system=getattr(Texts.SystemsNames, data["system"]))
            )
        case "manual":
            if data["system"] == "mes":
                await state.set_state(Authorization.username)
                await call.message.edit_text(
                    Texts.Authorization.AUTH_MANUAL_INFO_MES(
                        system=getattr(Texts.SystemsNames, data["system"]),
                        domain="dnevnik.mos.ru" if data["system"] == "mes" else "myschool.mosreg.ru",
                        METHOD=Texts.Authorization.Methods.mosru
                    )
                )
                await call.message.answer(
                    Texts.Authorization.MES_ENTER_USERNAME,
                    disable_web_page_preview=True
                )
            else:
                await state.set_state(Authorization.auth_type)
                await call.message.edit_text(
                    Texts.Authorization.AUTH_MANUAL_INFO_MY_SCHOOL(
                        system=getattr(Texts.SystemsNames, data["system"]),
                        domain="dnevnik.mos.ru" if data["system"] == "mes" else "myschool.mosreg.ru",
                        METHOD="?",
                        BLOCKQUOTE=Texts.Authorization.CHOOSE_AUTH_TYPE
                    ),
                    reply_markup=LOGIN_METHODS_MY_SCHOOL
                )


@router.callback_query(Authorization.web, F.data == "back")
@router.callback_query(Authorization.token, F.data == "back")
@router.callback_query(Authorization.auth_type, F.data == "back")
async def auth_back(call: CallbackQuery, state: FSMContext):
    await set_system(call, state, back=True)


@router.message(Authorization.web, Command("start"), F.text.regexp(r"/start web_auth_(.*)").as_("match"))
async def web_auth_result(message: Message, state: FSMContext, match: re.Match, bot: Bot):
    if not await state.get_state():
        await message.react([ReactionTypeEmoji(emoji="🤨")])
        return

    match match.group(1):
        case "failed":
            await message.answer(Texts.Authorization.WEB_AUTH_FAILED)
            return

        case "success":
            resp = requests.post(
                f"https://octodiary.den4iksop.org/bot-auth/{message.from_user.id}",
                verify=False
            ).json()

            if resp.get("status") == "Failed":
                await message.answer(Texts.Authorization.WEB_AUTH_FAILED_2)
                return

            await state.update_data(
                token=resp["token"],
                system=resp["system"]
            )

            response = await message.answer(Texts.LOADING)

            await check_data(response, token=resp["token"], state=state, bot=bot)
        case _:
            if not await state.get_state():
                await message.react([ReactionTypeEmoji(emoji="🤨")])
                return


@router.message(Authorization.token, F.text.regexp(r"^([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_\-\+\/=]*)"))
async def token(message: Message, state: FSMContext, bot: Bot):
    try:
        jwt.decode(message.text, options={"verify_signature": False})
    except: # noqa
        await message.answer(Texts.Authorization.INVALID_TOKEN)
        return

    await state.update_data(token=message.text)
    response = await message.answer(Texts.LOADING)

    await check_data(response, token=message.text, state=state, bot=bot)


@router.callback_query(Authorization.auth_type, F.data.in_(Texts.LoginMethods.keys()))
async def auth_by_type(call: CallbackQuery, state: FSMContext):
    await state.update_data(login_type=call.data)
    await state.set_state(Authorization.username)
    await call.message.edit_reply_markup(None)
    data = await state.get_data()

    await call.message.edit_text(
        Texts.Authorization.AUTH_MANUAL_INFO_MY_SCHOOL(
            system=getattr(Texts.SystemsNames, data["system"]),
            domain="dnevnik.mos.ru" if data["system"] == "mes" else "myschool.mosreg.ru",
            METHOD=getattr(Texts.Authorization.Methods, call.data),
            BLOCKQUOTE=Texts.Authorization.NEED_LOGPASS(
                LOGIN_SYSTEM_HTML={
                    "logpass": "<a href=\"https://myschool.morseg.ru/\">Моей Школы</a>",
                    "gosuslugi": "<a href=\"https://www.gosuslugi.ru/\">Госуслуг</a>",
                }[call.data]
            )
        )
    )
    await call.message.answer(
        (
            Texts.Authorization.GOSUSLUGI_ENTER_USERNAME
            if call.data == "gosuslugi"
            else Texts.Authorization.MY_SCHOOL_ENTER_USERNAME
        ),
        disable_web_page_preview=True
    )


@router.message(Authorization.username)
async def set_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(Authorization.password)
    await message.answer(
        Texts.Authorization.ENTER_PASSWORD
    )


@router.message(Authorization.password)
async def set_password(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(password=message.text)
    response = await message.answer(Texts.LOADING)

    await check_data(response, state=state, bot=bot)


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


async def send_mfa_user_request(
        api: AsyncMobileAPI,
        message: Message
):
    mfa_method = api._mfa_details["type"] # noqa
    if mfa_method == "SMS":
        phone = api._mfa_details["otp_details"]["phone"] # noqa
        await message.answer(
            text=Texts.Authorization.MFA_ENTER_OTP(PHONE=phone),
            parse_mode="HTML"
        )
    else:
        await message.answer(text=Texts.Authorization.MFA_ENTER_TTP)


@router.message(Authorization.gosuslugi_mfa, F.text.isdigit(), F.text.len() == 6)
async def set_gosuslugi_mfa(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    try:
        api: AsyncMobileAPI = data["api"]
        response = await api.esia_enter_MFA(code=int(message.text))
    except APIError as e:
        await state.clear()
        if e.error_types in ["INVALID_TTP", "INVALID_OTP"]:
            await message.answer(text=Texts.Authorization.INVALID_MFA)
        else:
            await message.answer(Texts.Authorization.ERROR_TRY_AGAIN(ERROR=str(e)))
            raise e
    else:
        if isinstance(response, Captcha):
            await state.update_data(captcha=response)
            await state.set_state(Authorization.gosuslugi_captcha)
            await send_captcha(response=response, message=message, bot=bot)
        else:
            response_msg = await message.answer(Texts.LOADING)
            await check_data(response_msg, response, state=state, bot=bot)


@router.message(Authorization.gosuslugi_captcha)
async def answer_gosuslugi_captcha(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    captcha: Captcha = data["captcha"]

    try:
        response = await (
            captcha.async_asnwer_captcha
            if captcha.question
            else captcha.async_verify_captcha
        )(answer=message.text) # noqa
    except APIError as e:
        if e.error_types == "INVALID_PASSWORD":
            await state.update_data(username=None, password=None)
            await state.set_state(Authorization.username)
            await message.answer(
                Texts.Authorization.INVALID_PASSWORD
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
            response_msg = await message.answer(Texts.LOADING)
            await check_data(response_msg, response, state=state, bot=bot)


@router.message(Authorization.blitz_otp, F.text.isdigit(), F.text.len() == 6)
async def set_blitz_otp(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    enter_code: EnterSmsCode = data["enter_code"]

    try:
        response: str = await enter_code.async_enter_code(message.text) # noqa
    except APIError as e:
        match e.error_types:
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
        response_msg = await message.answer(Texts.LOADING)
        await check_data(response_msg, response, state=state, bot=bot)


@router.callback_query(Authorization.confirm, F.data == "yes")
async def confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    await call.answer("OK!")
    response = await call.message.edit_text(Texts.LOADING)

    data = await state.get_data()
    await state.clear()
    user = database.user(str(call.from_user.id))

    database.settings.set(
        "users",
        list({*database.settings.get("users", []), call.from_user.id})
    )
    database.settings.set(
        "users_dt",
        {**database.settings.get("users_dt", {}), call.from_user.id: get_date().strftime("%Y-%m-%d")}
    )

    user.db_users_profile_info = [prof.model_dump() for prof in data["users_profile_info"]]
    user.db_profile_id = data["profile_id"]
    user.token = data["token"]
    user.system = data["system"]

    user.db_settings = {
        "goals": False,
        "notifications": {
            "create_mark": True
        }
    }
    user.db_skip_notifications = True

    print("OOPS!")
    await UserData(user, user.apis).load_all(bot)

    await response.answer(
        text=Texts.Authorization.SUCCESS_CONFIRM,
        reply_markup=root_menu(user.system)
    )
    await response.delete()


@router.callback_query(Authorization.confirm, F.data == "no")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(Texts.Authorization.CANCEL)


async def app_auth(message: Message, state: FSMContext, match: re.Match, bot: Bot):
    token_hex = match.group(1)

    info: dict[str, str] = requests.get("https://octodiary.den4iksop.org/token_info?token_hex=" + token_hex, timeout=10).json()

    await state.update_data(
        token=info["token"],
        system=info["system"]
    )

    response = await message.answer(Texts.LOADING)

    await check_data(response, token=info["token"], state=state, bot=bot)
