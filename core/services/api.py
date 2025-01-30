#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import datetime
import enum
import pickle
import typing
from datetime import timedelta

import jwt
from aiogram import Bot
from loguru import logger
from octodiary.types.mobile import FamilyProfile, EventsResponse, SubjectsMarks, ShortHomeworks, Marks, \
    LessonScheduleItem
from octodiary.urls import BaseURL, URLTypes
from pydantic import BaseModel

from core.misc.additional_models import MarkInfo, Homeworks
from core.misc.apis import APIs
from core.misc.texts import Texts
from core.misc.utils import get_date, TIMEZONE, get_week_for_date, get_datetime, send_message
from core.services.database import User, database
from core.services.octodiary_x import refresh_token

ResponseType = typing.TypeVar("ResponseType")


class APIResponse(BaseModel, typing.Generic[ResponseType]):
    data: ResponseType
    is_cache: bool = False
    last_cache_time: typing.Optional[str] = None


class DataType(enum.Enum):
    MATERIAL_LAUNCH_LINK = "material_launch_link"
    PROFILE_ID = "profile_id"
    PROFILE = "profile"
    EVENTS = "events"
    HOMEWORKS = "homeworks"
    MARKS_BY_DATE = "marks_by_date"
    MARKS_BY_SUBJECT = "marks_by_subject"
    SCHEDULE_ITEM = "schedule_item"
    MARK = "mark"


class UserData:
    db_user: User
    apis: APIs
    data: dict[DataType, typing.Any]

    MODELS = {
        DataType.PROFILE: FamilyProfile,
        DataType.EVENTS: EventsResponse,
        DataType.HOMEWORKS: ShortHomeworks,
        DataType.MARKS_BY_DATE: Marks,
        DataType.MARKS_BY_SUBJECT: SubjectsMarks,
        DataType.SCHEDULE_ITEM: LessonScheduleItem
    }

    def __init__(self, user: User, apis: APIs):
        self.db_user = user
        self.apis = apis
        self.data = {}

        self.profile_id: typing.Optional[int] = None

    @classmethod
    async def refresh_token(cls, token: str) -> str:
        data = jwt.decode(token, options={"verify_signature": False})
        return await refresh_token(token, data, region=50 if "mosreg.ru" in data["iss"] else 77)

    async def get(self, name: DataType, **kwargs):
        """
        :param name:
        :param kwargs: begin_date/from_date, end_date, student_id, subject,
        :return:
        """
        today = get_date()
        match name:
            case DataType.PROFILE_ID:
                return (await self.apis.mobile.get_users_profile_info())[0].id
            case DataType.PROFILE:
                return await self.apis.mobile.get_family_profile(profile_id=self.profile_id)
            case DataType.EVENTS:
                return await self.apis.mobile.get_events(
                    person_id=(
                        self.db_user.db_current_child["contingent_guid"]
                        if self.db_user.db_current_child
                        else (
                            self.data[DataType.PROFILE].children[0].id
                            if DataType.PROFILE in self.data
                            else self.db_user.db_profile["children"][0]["contingent_guid"]
                        )
                    ),
                    mes_role=(
                        self.data[DataType.PROFILE].profile.type
                        if DataType.PROFILE in self.data
                        else self.db_user.db_profile["profile"]["type"]
                    ),
                    begin_date=kwargs.get("begin_date", None) or (today - timedelta(days=-1 * (0 - today.weekday()))),
                    end_date=kwargs.get("end_date", None) or (today + timedelta(days=7 + (6 - today.weekday()))),
                )
            case DataType.MARKS_BY_DATE:
                return await self.apis.mobile.get_marks(
                    student_id=(
                        kwargs.get("student_id", None)
                        or (
                            self.db_user.db_current_child["id"]
                            if self.db_user.db_current_child
                            else (
                                self.data[DataType.PROFILE].children[0].id
                                if DataType.PROFILE in self.data
                                else self.db_user.db_profile["children"][0]["id"]
                            )
                        )
                    ),
                    profile_id=self.db_user.db_profile_id,
                    from_date=kwargs["from_date"],
                    to_date=kwargs["to_date"]
                )
            case DataType.MARKS_BY_SUBJECT:
                return await self.apis.mobile.get_subjects_marks(
                    student_id=(
                        kwargs.get("student_id", None)
                        or (
                            self.db_user.db_current_child["id"]
                            if self.db_user.db_current_child
                            else (
                                self.data[DataType.PROFILE].children[0].id
                                if DataType.PROFILE in self.data
                                else self.db_user.db_profile["children"][0]["id"]
                            )
                        )
                    ),
                    profile_id=self.db_user.db_profile_id
                )
            case DataType.HOMEWORKS:
                return await self.apis.mobile.request(
                    method="GET",
                    base_url=BaseURL(type=URLTypes.SCHOOL_API, system=self.db_user.system),
                    path="/family/mobile/v1/homeworks",
                    params={
                        "student_id": (
                            kwargs.get("student_id", None)
                            or (
                                self.db_user.db_current_child["id"]
                                if self.db_user.db_current_child
                                else (
                                    self.data[DataType.PROFILE].children[0].id
                                    if DataType.PROFILE in self.data
                                    else self.db_user.db_profile["children"][0]["id"]
                                )
                            )
                        ),
                        "from": kwargs.get("from_date"),
                        "to": kwargs.get("to_date"),
                    },
                    custom_headers={
                        "x-mes-subsystem": "familymp",
                        "client-type": "diary-mobile",
                        "profile-id": self.db_user.db_profile_id,
                    },
                    model=Homeworks,
                )
            case DataType.MATERIAL_LAUNCH_LINK:
                return await self.apis.mobile.request(
                    method="GET",
                    base_url=BaseURL(type=URLTypes.DNEVNIK if self.db_user.system == "mes" else URLTypes.SCHOOL, system=self.db_user.system),
                    path="/ej/family/homework/launch",
                    params={
                        "homework_entry_id": kwargs.get("homework_entry_id"),
                        "material_id": kwargs.get("material_id"),
                    },
                    custom_headers={
                        "x-mes-subsystem": "familymp"
                    },
                    return_raw_text=True
                )
            case DataType.SCHEDULE_ITEM:
                return await self.apis.mobile.get_lesson_schedule_item(
                    profile_id=self.db_user.db_profile_id,
                    student_id=(
                        kwargs.get("student_id", None)
                        or (
                            self.db_user.db_current_child["id"]
                            if self.db_user.db_current_child
                            else (
                                self.data[DataType.PROFILE].children[0].id
                                if DataType.PROFILE in self.data
                                else self.db_user.db_profile["children"][0]["id"]
                            )
                        )
                    ),
                    lesson_id=kwargs.get("lesson_id"), type=kwargs.get("lesson_type")
                )
            case DataType.MARK:
                return await self.apis.mobile.request(
                    method="GET",
                    base_url=BaseURL(type=URLTypes.SCHOOL_API, system=self.db_user.system),
                    path=f"/family/mobile/v1/marks/{kwargs['mark_id']}",
                    params={
                        "student_id": (
                            kwargs.get("student_id", None)
                            or (
                                self.db_user.db_current_child["id"]
                                if self.db_user.db_current_child
                                else (
                                    self.data[DataType.PROFILE].children[0].id
                                    if DataType.PROFILE in self.data
                                    else self.db_user.db_profile["children"][0]["id"]
                                )
                            )
                        ),
                    },
                    custom_headers={
                        "x-mes-subsystem": "familymp",
                        "client-type": "diary-mobile",
                        "profile-id": self.db_user.db_profile_id,
                    },
                    model=MarkInfo
                )

    async def get_cached(self, name: DataType, key: str = None, raw: bool = False):
        raw_data = await database.redis.get(key or f"user:{self.db_user.id}:{name}")
        if not raw_data:
            return None

        return UserData.MODELS[name].model_validate(
            pickle.loads(
                raw_data
            )
        ) if not raw else pickle.loads(raw_data)

    async def load(self, name: DataType, on_loaded=None, on_error=None, **kwargs):
        try:
            self.data[name] = await self.get(name, **kwargs)
            await self.log(str(name))
            if on_loaded:
                await on_loaded

            return self.data[name]
        except Exception as e:
            await self.log(str(name), False)
            if on_error:
                await on_error
            else:
                raise e

    async def load_all(self, bot: Bot):
        await self.check_token()
        try:
            self.profile_id = await self.load(DataType.PROFILE_ID)
            self.db_user.db_profile_id = self.profile_id
            self.db_user.db_profile = (await self.load(DataType.PROFILE)).model_dump(
                mode="json",
                exclude={"children": {"__all__": {"groups"}, "hash": True}},
                exclude_none=True,
                exclude_unset=True
            )
        except Exception as e:
            raise e
            return False, e  # noqa

        date = get_date()
        weeks = [
            week
            for i in range(-self.db_user.db_settings.get("weeks_offset", 2), self.db_user.db_settings.get("weeks_offset", 2) + 1)
            if (week := get_week_for_date(date + timedelta(weeks=i)))
        ]

        time = get_datetime()
        events = {"datetime": time.isoformat()}
        homeworks = {"datetime": time.isoformat()}
        marks_by_date = {"datetime": time.isoformat()}

        for week in weeks:
            try:
                marks_by_date[week[0].isoformat()] = (await self.get(
                    DataType.MARKS_BY_DATE,
                    from_date=week[0],
                    to_date=week[-1]
                )).model_dump(
                    mode="json"
                )
            except Exception:
                marks_by_date[week[0].isoformat()] = []

            try:
                events[week[0].isoformat()] = (await self.get(
                    DataType.EVENTS,
                    begin_date=week[0],
                    to_date=week[-1]
                )).model_dump(
                    mode="json",
                    exclude={"response": {"__all__": {"class_unit_ids"}}},
                )
            except Exception:
                events[week[0].isoformat()] = None

            try:
                homeworks[week[0].isoformat()] = (await self.get(
                    DataType.HOMEWORKS,
                    from_date=week[0],
                    to_date=week[-1]
                )).model_dump(
                    mode="json",
                )
            except Exception:
                homeworks[week[0].isoformat()] = None

        self.data[DataType.EVENTS] = events
        self.data[DataType.HOMEWORKS] = homeworks
        self.data[DataType.MARKS_BY_DATE] = marks_by_date

        await self.load(DataType.MARKS_BY_SUBJECT)

        await self.cache_data()

    async def cache_data(self, name: DataType = None, raw: bool = False):
        if name:
            await database.redis.set(
                f"user:{self.db_user.id}:{name}",
                pickle.dumps(
                    self.data[name].model_dump(
                        mode="json",
                        exclude=(
                            {"children": {"__all__": {"groups"}, "hash": True}}
                            if name == DataType.PROFILE
                            else {"response": {"__all__": {"class_unit_ids"}}}
                            if name == DataType.EVENTS
                            else None
                        ),
                        exclude_none=True,
                        exclude_unset=True,
                    ) if not raw else self.data[name]
                )
            )
        else:
            for name in self.data:
                if name != DataType.PROFILE_ID:
                    await self.cache_data(name, raw=True if name in [
                        DataType.EVENTS,
                        DataType.HOMEWORKS,
                        DataType.MARKS_BY_DATE
                    ] else False)

    async def log(self, name: str, success: bool = True, next_func=None):
        logger.log("MINIDEBUG", f"[UserData::loading::{'failed' if not success else 'success'}] {self.db_user.id} {name} is{' NOT' if not success else ''} loaded! ")

        if next_func:
            await next_func

    async def check_token(self):
        token = self.db_user.token
        if self.token_is_expired(token):
            raise RuntimeError("TokenExpired")

        data = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.datetime.fromtimestamp(
            data["exp"], tz=TIMEZONE
        )
        now = get_datetime()

        if abs(exp - now).total_seconds() <= 60 * 60 * 24 * 3:
            try:
                self.db_user.token = await UserData.refresh_token(token)
                return True
            except: # noqa
                raise RuntimeError("TokenExpired")

    @staticmethod
    async def token_is_expired(token: str):
        data = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.datetime.fromtimestamp(
            data["exp"], tz=TIMEZONE
        )
        return get_datetime() > exp
