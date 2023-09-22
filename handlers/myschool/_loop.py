#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
from datetime import date, timedelta
import datetime

import jwt
from aiogram import Bot
from database import Database
from loop import loop
from octodiary.asyncApi.myschool import AsyncMobileAPI, AsyncWebAPI
from octodiary.exceptions import APIError
from octodiary.types.myschool.mobile import EventsResponse, Notification
from utils.other import mark, pluralization_string

from .router import router as MySchoolRouter

db = Database()

@MySchoolRouter.startup()
@loop(600)
async def on_startup_myschool_router(**kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == "myschool"
    }:
        await asyncio.sleep(1)
        try:
            api = AsyncMobileAPI(token=user.token)
            profile_id = (await api.get_users_profile_info())[0].id
            profile = await api.get_profile(profile_id)
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


def generate_text_notification(notif: Notification):
    text = "🔔 <b>Новое уведомление</b>"
    match notif.event_type:
        case "create_mark":
            text += " [<code>Оценка</code>]\n\n"
            text += f"┌ <b>Предмет</b>: <code>{notif.subject_name}</code>\n"
            if notif.old_mark_value:
                text += f"├ <b>Старая</b> оценка: <code>{notif.old_mark_value}</code>\n"
            text += f"├ <b>Новая оценка</b>: <code>{mark(notif.new_mark_value, notif.new_mark_weight)}</code>\n"
            text += f"├ <b>Тип</b> работы: <code>{notif.control_form_name}</code> - {pluralization_string(notif.new_mark_weight, ['балл', 'балла', 'баллов'])} {'❗️' if notif.new_is_exam else ''}\n"
            text += f"└ <b>Дата и время</b> урока: <code>{notif.lesson_date}</code>\n\n"
            text += f"<tg-spoiler>#newMark #notification #date_{notif.datetime[:10].replace('-', '_')}</tg-spoiler>"
        
        case _:
            return ""

    return text


@MySchoolRouter.startup()
@loop(60 * 1.5)
async def send_notications(bot: Bot, **kwargs):
    for user_id, user in {
        user_id: db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == "myschool"
    }.items():
        await asyncio.sleep(1)
        if not (settings := user.db_settings) or not settings.get("notifications", True):
            continue
        api = AsyncMobileAPI(token=user.token)
        try:
            notifications = await api.get_notifications(
                profile_id=user.db_profle_id,
                student_id=user.db_profile["children"][0]["id"]
            )
        except APIError:
            notifications = []
        notifications.reverse()

            
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
                user.db_notified_ids = user.db_notified_ids + [id]
                continue

            if (
                settings.get("notifications", {}).get(notification.event_type, True)
                and id not in user.db_notified_ids
                and (text := generate_text_notification(notification))
            ):
                await bot.send_message(int(user_id), text)
                user.db_notified_ids = user.db_notified_ids + [id]
        
        if user.db_skip_notifications:
            user.db_skip_notifications = False


@MySchoolRouter.startup()
@loop(60)
async def refresh_tokens(bot: Bot, **kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == "myschool"
    }:
        await asyncio.sleep(1)
        exp = datetime.datetime.fromtimestamp(
            jwt.decode(user.token, options={"verify_signature": False})["exp"]
        )
        now = datetime.datetime.now()
        if (now.year, now.month, now.day, now.hour-1, now.minute) < (exp.year, exp.month, exp.day, exp.hour, exp.minute) > (now.year, now.month, now.day, now.hour, now.minute):
            user.token = await AsyncWebAPI(token=user.token).refresh_token(0, 0)

