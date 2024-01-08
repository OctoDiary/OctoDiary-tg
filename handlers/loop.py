#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import datetime
from datetime import timedelta

import jwt
from aiogram import Bot, Router, exceptions

import api
from apis import MesAPIs, MySchoolAPIs
from database import Database
from handlers.scheduler import run_scheduler_for_chat
from loop import loop
from octodiary.asyncApi.myschool import AsyncWebAPI
from octodiary.exceptions import APIError
from octodiary.types.mes.mobile.marks import Payload
from octodiary.types.myschool.mobile import EventsResponse
from octodiary.types.myschool.mobile.marks import PayloadItem
from utils.filters import user_apis
from utils.other import TIMEZONE, get_date, mark, pluralization_string
from utils.texts import Texts

db = Database()
LoopRouter = Router()


async def save_user_data(user_id):
    user = db.user(str(user_id))

    try:
        if user.system == Texts.Systems.MY_SCHOOL:
            apis = MySchoolAPIs(token=user.token)
        else:
            apis = MesAPIs(token=user.token)

        profile_id = (await api.get_profile_users_info(user=user, apis=apis))[0].id
        profile = await api.get_profile(user=user, profile_id=profile_id, apis=apis)

        user.db_profile_id = profile_id
        user.db_profile = profile.model_dump(
            exclude={"children": {"__all__": {"groups"}, "hash": True}},
            exclude_none=True,
            exclude_unset=True,
        )

        today = get_date()
        events: EventsResponse = await api.get_events(
            user=user,
            apis=apis,
            begin_date=today - timedelta(days=-1 * (0 - today.weekday())),
            end_date=today + timedelta(days=7 + (6 - today.weekday())),
            profile=profile
        )
        user.db_events = events.model_dump(
            exclude={"response": {"__all__": {"materials", "class_unit_ids"}}},
            exclude_none=True,
            exclude_unset=True,
        )
    except APIError:
        pass


@LoopRouter.startup()
@loop(900)
async def save_users_data_loop(**kwargs):
    for func in [
        save_user_data(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.user(user_id).system in [
            Texts.Systems.MY_SCHOOL,
            Texts.Systems.MES
        ] and db.user(user_id).token
    ]:
        await func


def generate_text_notification(
        mark_data: PayloadItem | Payload,
        *,
        edited: bool = False,
        old_mark_value: str = "",
        child_name: str
):
    text = Texts.Notifications.TITLE
    if edited:
        texts = Texts.Notifications.EditedMark
    else:
        texts = Texts.Notifications.Mark

    text += texts.SUBTITLE(CHILD_NAME=child_name)
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
    if mark_data.comment:
        text += texts.COMMENT(
            COMMENT=mark_data.comment
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

    apis = user_apis(user)

    if user.db_settings.get("notifications", {}).get("create_mark", False):
        for child in user.db_profile["children"]:
            try:
                marks = sorted(
                    (
                        await api.get_marks(
                            user=user,
                            apis=apis,
                            from_date=get_date() - timedelta(weeks=3),
                            to_date=get_date(),
                            student_id=child["id"],
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
                    user.save()
                    continue

                if ID in user.db_notified_marks_ids and user.db_notified_marks_ids[ID] == mark_data.value:
                    continue

                edited = ID in user.db_notified_marks_ids and user.db_notified_marks_ids[ID] != mark_data.value
                text = generate_text_notification(
                    mark_data,
                    edited=edited,
                    child_name=(
                        f"[ {child['first_name']} | {child['class_name']} ]"
                        if len(user.db_profile["children"]) > 1
                        else ""
                    ),
                )

                sent = False
                while not sent:
                    try:
                        await bot.send_message(int(user_id), text)
                        sent = True
                    except exceptions.TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)

                user.db_notified_marks_ids = user.db_notified_marks_ids | {ID: mark_data.value}
                user.save()
                await asyncio.sleep(2)

    if user.db_skip_notifications:
        user.db_skip_notifications = False


@LoopRouter.startup()
@loop(150)
async def send_notifications(bot: Bot, **kwargs):
    for func in [
        check_user_notifications(user_id, bot)
        for user_id in db.keys()
        if user_id.isdigit() and db.user(user_id).system in [
            Texts.Systems.MY_SCHOOL,
            Texts.Systems.MES
        ] and db.user(user_id).token
    ]:
        await func


@LoopRouter.startup()
@loop(60)
async def refresh_tokens(**kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None) == Texts.Systems.MY_SCHOOL
    }:
        await asyncio.sleep(1)
        exp = datetime.datetime.fromtimestamp(
            jwt.decode(user.token, options={"verify_signature": False})["exp"], tz=TIMEZONE
        )
        now = datetime.datetime.now(tz=TIMEZONE)
        if abs(exp - now).total_seconds() <= 3600:
            user.token = await AsyncWebAPI(token=user.token).refresh_token(0, 0)


@LoopRouter.startup()
@loop(900)
async def scheduler_loop(bot: Bot, **kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.user(user_id).system in [
            Texts.Systems.MY_SCHOOL,
            Texts.Systems.MES
        ] and db.user(user_id).token
    }:
        await asyncio.sleep(1)
        scheduler = user.db_scheduler
        if not scheduler:
            continue

        for chat_id in scheduler:
            await run_scheduler_for_chat(
                chat_id=chat_id,
                apis=(
                    MesAPIs(token=user.token)
                    if user.system == Texts.Systems.MES
                    else MySchoolAPIs(token=user.token)
                ),
                user=user,
                bot=bot,
            )
