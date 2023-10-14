#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import datetime
from datetime import date, timedelta

import jwt
from aiogram import Bot, exceptions

from database import Database
from handlers.mes.router import APIs, router as MesRouter
from handlers.mes.scheduler import run_scheduler_for_chat
from loop import loop
from octodiary.asyncApi.mes import AsyncMobileAPI
from octodiary.exceptions import APIError
from octodiary.types.mes.mobile import EventsResponse, Notification
from utils.other import mark, pluralization_string
from utils.texts import Texts

db = Database()


async def save_mes_user_data(user_id):
    user = db.user(str(user_id))
    
    try:
        api = AsyncMobileAPI(token=user.token)
        profile_id = (await api.get_users_profiles_info())[0].id
        profile = await api.get_family_profile(profile_id)
        today = date.today()
        events: EventsResponse = await api.get_events(
            person_id=profile.children[0].contingent_guid,
            mes_role=profile.profile.type,
            begin_date=(
                today - timedelta(days= -1*(0 - today.weekday()))
            ),
            end_date=(
                today + timedelta(days= 7+(6 - today.weekday()))
            )
        )
        notifications = await api.get_notifications(profile_id=profile_id, student_id=profile.children[0].id)

        user.db_profle_id = profile_id
        user.db_profile = profile.model_dump(
            exclude={"children": {"__all__": {"groups"}, "hash": True}},
            exclude_none=True,
            exclude_unset=True,
        )
        user.db_events = events.model_dump(
            exclude={"response": {"__all__": {"materials", "class_unit_ids"}}},
            exclude_none=True,
            exclude_unset=True,
        )
        user.db_notifications = [
            x.model_dump(exclude_none=True, exclude_unset=True)
            for x in notifications
        ]
    except APIError:
        pass


@MesRouter.startup()
@loop(600)
async def save_users_data_loop(**kwargs):
    for func in [
        save_mes_user_data(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == Texts.Systems.MES
    ]:
        await func


def generate_text_notification(notif: Notification):
    text = Texts.Notifications.TITLE
    match notif.event_type:
        case "create_mark":
            text += Texts.Notifications.Mark.SUBTITLE
            text += Texts.Notifications.Mark.SUBJECT(
                SUBJECT_NAME=notif.subject_name
            )
            if notif.old_mark_value:
                text += Texts.Notifications.Mark.OLD_MARK(
                    MARK=str(notif.old_mark_value)
                )
            text += Texts.Notifications.Mark.NEW_MARK(
                MARK=mark(notif.new_mark_value, notif.new_mark_weight)
            )
            text += Texts.Notifications.Mark.WORK_TYPE(
                CONTROL_FORM_NAME=notif.control_form_name,
                WEIGHT=pluralization_string(
                    notif.new_mark_weight,
                    ["балл", "балла", "баллов"]
                ),
                IS_EXAM_EMOJI="❗️" if notif.new_is_exam else ""
            )
            text += Texts.Notifications.Mark.LESSON_TIME(
                TIME=str(notif.lesson_date)
            )
            text += Texts.Notifications.Mark.HASHTAGS(
                DATE=notif.datetime[:10].replace("-", "_")
            )
        case _:
            return ""

    return text


async def check_user_notifications(user_id, bot: Bot):
    user = db.user(user_id)
    if user.db_settings.get("skip_notifications", False):
        return
    
    api = AsyncMobileAPI(token=user.token)
    try:
        notifications = await api.get_notifications(
            profile_id=user.db_profle_id,
            student_id=user.db_profile["children"][0]["id"]
        )
        notifications.reverse()
    except APIError:
        return
    
    for notification in notifications:
        id = int(
            notification
                .datetime
                    .replace("-", "")
                    .replace(" ", "")
                    .replace(":", "")
                    .replace(".", "")
        )
        if user.db_skip_notifications:
            user.db_notified_ids = [*user.get("notified_ids", []), id]
            continue

        if (
            user.db_settings.get("notifications", {}).get(notification.event_type, False)
            and id not in user.get("notified_ids", [])
            and (text := generate_text_notification(notification))
        ):
            try:
                await bot.send_message(int(user_id), text)
            except exceptions.TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                await bot.send_message(int(user_id), text)
            
            user.db_notified_ids = [*user.db_notified_ids, id]
            await asyncio.sleep(2)

    if user.db_skip_notifications:
        user.db_skip_notifications = False


@MesRouter.startup()
@loop(60 * 1.5)
async def send_notications(bot: Bot, **kwargs):
    for func in [
        asyncio.create_task(check_user_notifications(user_id, bot))
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == Texts.Systems.MES
    ]:
        await func


@MesRouter.startup()
@loop(60)
async def refresh_tokens(**kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == Texts.Systems.MES
    }:
        await asyncio.sleep(1)
        exp = datetime.datetime.fromtimestamp(
            jwt.decode(user.token, options={"verify_signature": False})["exp"]
        )
        now = datetime.datetime.now()
        if (now.year, now.month, now.day, now.hour-1, now.minute) < (exp.year, exp.month, exp.day, exp.hour, exp.minute) > (now.year, now.month, now.day, now.hour, now.minute):
            user.token = await AsyncMobileAPI(token=user.token).refresh_token()


@MesRouter.startup()
@loop(60 * 2.5)
async def scheduler_loop(bot: Bot, **kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == Texts.Systems.MES
    }:
        await asyncio.sleep(1)
        scheduler = user.db_scheduler
        if not scheduler:
            continue

        for chat_id in scheduler:
            await run_scheduler_for_chat(
                chat_id=chat_id,
                apis=APIs(token=user.token),
                user=user,
                bot=bot,
            )
