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
from handlers.mes.router import APIs
from handlers.mes.router import router as MesRouter
from handlers.mes.scheduler import run_scheduler_for_chat
from loop import loop
from octodiary.asyncApi.mes import AsyncMobileAPI
from octodiary.exceptions import APIError
from octodiary.types.mes.mobile import EventsResponse
from octodiary.types.mes.mobile.marks import Payload
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
                    today - timedelta(days=-1 * (0 - today.weekday()))
            ),
            end_date=(
                    today + timedelta(days=7 + (6 - today.weekday()))
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


def generate_text_notification(mark_data: Payload, *, edited: bool = False, old_mark_value: str = ""):
    text = Texts.Notifications.TITLE
    if edited:
        texts = Texts.Notifications.EditedMark
    else:
        texts = Texts.Notifications.Mark

    text += texts.SUBTITLE
    text += texts.SUBJECT(
        SUBJECT_NAME=mark_data.subject_name
    )
    if edited:
        text += texts.OLD_MARK(MARK=old_mark_value)
    text += texts.NEW_MARK(
        MARK=mark(mark_data.value, mark_data.weight)
    )
    text += texts.WORK_TYPE(
        CONTROL_FORM_NAME=mark_data.control_form_name,
        WEIGHT=pluralization_string(
            mark_data.weight,
            ["балл", "балла", "баллов"]
        ),
        IS_EXAM_EMOJI="❗️" if mark_data.is_exam else ""
    )
    text += texts.LESSON_DATE(
        TIME=str(mark_data.date)
    )
    text += texts.HASHTAGS(
        DATE=mark_data.updated_at[:10].replace("-", "_")
    )
    return text


async def check_user_notifications(user_id, bot: Bot):
    user = db.user(user_id)
    if user.db_notified_marks_ids is None:
        user.db_notified_marks_ids = {}

    if user.db_notified_ids:
        user.pop("notified_ids")
        user.db_skip_notifications = True

    api = AsyncMobileAPI(token=user.token)

    if user.db_settings.get("notifications", {}).get("create_mark", False):
        try:
            marks = sorted(
                (
                    await api.get_marks(
                        student_id=user.db_profile["children"][0]["id"],
                        profile_id=user.db_profile_id,
                        from_date=date.today() - timedelta(weeks=3),
                        to_date=date.today()
                    )
                ).payload,
                key=lambda x: datetime.datetime.fromisoformat(x.updated_at),
                reverse=True
            )
        except APIError:
            return

        for mark_data in marks:
            ID = str(mark_data.id)
            if user.db_skip_notifications:
                user.db_notified_marks_ids[ID] = mark_data.value
                continue

            if ID in user.db_notified_marks_ids:
                if user.db_notified_marks_ids[ID] != mark_data.value:
                    await bot.send_message(int(user_id), generate_text_notification(mark_data, edited=True))
                    user.db_notified_marks_ids[ID] = mark_data.value
                continue

            try:
                await bot.send_message(int(user_id), generate_text_notification(mark_data))
            except exceptions.TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                await bot.send_message(int(user_id), generate_text_notification(mark_data))

            user.db_notified_marks_ids = user.db_notified_marks_ids | {ID: mark_data.value}
            user.save()
            await asyncio.sleep(2)

    if user.db_skip_notifications:
        user.db_skip_notifications = False


@MesRouter.startup()
@loop(150)
async def send_notifications(bot: Bot, **kwargs):
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
        if abs(exp - now).total_seconds() <= 3600:
            user.token = await AsyncMobileAPI(token=user.token).refresh_token()


@MesRouter.startup()
@loop(600)
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
