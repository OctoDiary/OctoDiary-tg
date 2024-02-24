#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import asyncio
import datetime
from contextlib import suppress
from datetime import timedelta

import jwt
from aiogram import Bot, Router, exceptions

import api
from apis import APIs
from database import Database
from handlers.scheduler import run_scheduler_for_chat
from loop import loop
from octodiary.exceptions import APIError
from octodiary.types.mobile import EventsResponse
from octodiary.types.mobile.marks import Payload
from utils.filters import user_apis
from utils.other import TIMEZONE, get_date, get_datetime, mark, pluralization_string
from utils.texts import Texts

db = Database()
LoopRouter = Router()


async def save_user_data(user_id, bot: Bot):
    user = db.user(str(user_id))

    try:
        apis = APIs(token=user.token, system=user.system)

        profile_id = (await api.get_profile_users_info(apis=apis))[0].id
        profile = (await api.get_profile(user=user, profile_id=profile_id, apis=apis)).response

        user.db_profile_id = profile_id
        user.db_profile = profile.model_dump(
            mode="json",
            exclude={"children": {"__all__": {"groups"}, "hash": True}},
            exclude_none=True,
            exclude_unset=True,
        )

        today = get_date()
        events: EventsResponse = (
            await api.get_events(
                user=user,
                apis=apis,
                begin_date=today - timedelta(days=-1 * (0 - today.weekday())),
                end_date=today + timedelta(days=7 + (6 - today.weekday())),
                profile=profile
            )
        ).response

        cache = {
            "profile": user.db_profile,
            "events": events.model_dump(
                mode="json",
                exclude={"response": {"__all__": {"class_unit_ids"}}},
                exclude_none=True,
                exclude_unset=True,
            ),
            "homeworks": {
                "upcoming": (
                    await api.get_homeworks(user=user, apis=apis, type=api.HomeworkTypes.UPCOMING)
                ).response.model_dump(mode="json", exclude_none=True, exclude_unset=True),
                "past": (
                    await api.get_homeworks(user=user, apis=apis, type=api.HomeworkTypes.PAST)
                ).response.model_dump(mode="json", exclude_none=True, exclude_unset=True)
            },
            "marks": {
                "by_date": (
                    await api.get_marks(
                        user=user,
                        apis=apis,
                        from_date=get_date() - timedelta(days=14),
                        to_date=get_date(),
                    )
                ).response.model_dump(mode="json", exclude_none=True, exclude_unset=True),
                "by_subject": (
                    await api.get_subjects_marks(user=user, apis=apis)
                ).response.model_dump(mode="json", exclude_none=True, exclude_unset=True)
            },
            "rating": {
                "class": [
                    x.model_dump(mode="json", exclude_none=True, exclude_unset=True)
                    for x in (
                        await api.get_rating(user=user, apis=apis, type=api.RatingType.CLASS)
                    ).response
                ],
                "subjects": [
                    x.model_dump(mode="json", exclude_none=True, exclude_unset=True)
                    for x in (
                        await api.get_rating(user=user, apis=apis, type=api.RatingType.SUBJECTS)
                    ).response
                ],
            },
            "class_members": [
                i.model_dump(mode="json", exclude_none=True, exclude_unset=True)
                for i in (
                    await api.get_class_members(user=user, apis=apis)
                ).response
            ],
            "time": get_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        }

        user.cache = cache

        if user.get("server-is-not-available-notified-id", 0):
            await bot.send_message(int(user_id), Texts.Errors.SERVER_IS_AVAILABLE, reply_to_message_id=user[
                "server-is-not-available-notified-id"
            ])
            del user["server-is-not-available-notified-id"]
    except APIError as e:
        if e.status_code >= 500 and not user.get("server-is-not-available-notified-id", 0):
            message = await bot.send_message(
                int(user_id),
                Texts.Errors.SERVER_IS_NOT_AVAILABLE.format(
                    SYSTEM=Texts.MES if user.system == Texts.Systems.MES else Texts.MY_SCHOOL,
                    STATUS_CODE=e.status_code,
                ),
            )
            user["server-is-not-available-notified-id"] = message.message_id


@LoopRouter.startup()
@loop(900)
async def save_users_data_loop(bot: Bot, **kwargs):
    for func in [
        save_user_data(user_id, bot)
        for user_id in db.keys()
        if user_id.isdigit() and db.user(user_id).system in [
            Texts.Systems.MY_SCHOOL,
            Texts.Systems.MES
        ] and db.user(user_id).token
    ]:
        await func


def generate_text_notification(
        mark_data: Payload,
        *,
        edited: bool = False,
        old_mark_value: str = "",
        child_name: str,
        hide_mark: bool
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
    text += (texts.NEW_MARK if not hide_mark else texts.HIDDEN_MARK)(
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
                    ).response.payload,
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
                    hide_mark=user.db_settings.get("notifications", {}).get("hide_mark", False)
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
        if user_id.isdigit() and db.user(user_id).system and db.user(user_id).token
    ]:
        await func


@LoopRouter.startup()
@loop(60)
async def refresh_tokens(**kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.get_key(user_id, "system", None)
    }:
        await asyncio.sleep(1)
        exp = datetime.datetime.fromtimestamp(
            jwt.decode(user.token, options={"verify_signature": False})["exp"], tz=TIMEZONE
        )
        now = datetime.datetime.now(tz=TIMEZONE)
        if abs(exp - now).total_seconds() <= 3600:
            with (suppress(Exception)):
                user.token = APIs(
                    token=user.token,
                    system=user.system
                ).mobile.refresh_token(
                    **(
                        user.refresh_data
                        if user.system == Texts.Systems.MES
                        else {}
                    )
                )


@LoopRouter.startup()
@loop(900)
async def scheduler_loop(bot: Bot, **kwargs):
    for user in {
        db.user(user_id)
        for user_id in db.keys()
        if user_id.isdigit() and db.user(user_id).system
    }:
        await asyncio.sleep(1)
        scheduler = user.db_scheduler
        if not scheduler:
            continue

        for chat_id in scheduler:
            await run_scheduler_for_chat(
                chat_id=chat_id,
                apis=APIs(token=user.token, system=user.system),
                user=user,
                bot=bot,
            )
