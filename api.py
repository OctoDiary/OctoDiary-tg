#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import enum
import logging
import typing
from datetime import date, datetime, timedelta
from typing import Optional

from pydantic import BaseModel

from apis import APIs
from database import User
from octodiary import types
from octodiary.urls import BaseURL, URLTypes
from utils.additional_models import MarkInfo
from utils.other import get_date

ResponseType = typing.TypeVar("ResponseType")


class APIResponse(BaseModel, typing.Generic[ResponseType]):
    response: ResponseType
    is_cache: bool = False
    last_cache_time: Optional[str] = None


class HomeworkTypes(enum.Enum):
    UPCOMING = 1
    PAST = 2


async def get_homeworks(
        user: User,
        apis: APIs,
        type: HomeworkTypes
) -> APIResponse[types.mobile.ShortHomeworks]:
    is_cache = False
    try:
        response = await apis.mobile.get_homeworks_short(
            student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
            profile_id=user.db_profile_id,
            from_date=get_date(),
            to_date=(get_date() + timedelta(days=14))
        ) if type == HomeworkTypes.UPCOMING else await apis.mobile.get_homeworks_short(
            student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
            profile_id=user.db_profile_id,
            from_date=get_date() - timedelta(days=14),
            to_date=get_date() - timedelta(days=1)
        )
    except Exception as e:
        logging.error("API-Exception", exc_info=e)
        if user.cache.get("homeworks", {}).get("upcoming" if type == HomeworkTypes.UPCOMING else "past", None):
            is_cache = True
            response = types.mobile.ShortHomeworks.model_validate(
                user.cache["homeworks"]["upcoming" if type == HomeworkTypes.UPCOMING else "past"]
            )
        else:
            raise e

    return APIResponse(response=response, is_cache=is_cache, last_cache_time=user.cache.get("time", "недавно"))


async def get_events(
        user: User,
        apis: APIs,
        begin_date: date,
        end_date: date,
        *,
        profile: types.mobile.FamilyProfile | dict = None
) -> APIResponse[types.mobile.EventsResponse]:
    is_cache = False

    if profile is None:
        profile = user.db_profile

    if not isinstance(profile, dict):
        profile = profile.model_dump()

    try:
        response = await apis.mobile.get_events(
            person_id=user.db_current_child["contingent_guid"] if user.db_current_child else profile["children"][0]["contingent_guid"],
            mes_role=profile["profile"]["type"],
            begin_date=begin_date,
            end_date=end_date
        )
    except Exception as e:
        logging.error("API-Exception", exc_info=e)
        if user.cache.get("events", None):
            is_cache = True
            response = types.mobile.EventsResponse.model_validate(user.cache["events"])
        else:
            raise e

    return APIResponse(response=response, is_cache=is_cache, last_cache_time=user.cache.get("time", "недавно"))


async def get_profile_users_info(apis: APIs):
    return await apis.mobile.get_users_profile_info()


async def get_profile(
        user: User,
        apis: APIs,
        profile_id: Optional[int] = None
) -> APIResponse[types.mobile.FamilyProfile]:
    is_cache = False

    try:
        response = await apis.mobile.get_family_profile(profile_id=profile_id or user.db_profile_id)
    except Exception as e:
        logging.error("API-Exception", exc_info=e)
        if user.cache.get("profile", None):
            is_cache = True
            response = types.mobile.FamilyProfile.model_validate(
                user.cache["profile"]
            )
        else:
            raise e

    return APIResponse(response=response, is_cache=is_cache, last_cache_time=user.cache.get("time", "недавно"))


async def get_marks(
        user: User,
        apis: APIs,
        from_date: datetime.date,
        to_date: datetime.date,
        *,
        student_id: Optional[int] = None
) -> APIResponse[types.mobile.Marks]:
    is_cache = False

    try:
        response = await apis.mobile.get_marks(
            student_id=student_id or user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
            profile_id=user.db_profile_id,
            from_date=from_date,
            to_date=to_date
        )
    except Exception as e:
        logging.error("API-Exception", exc_info=e)
        if user.cache.get("marks", {}).get("by_date", None):
            response = types.mobile.Marks.model_validate(user.cache["marks"]["by_date"])
            is_cache = True
        else:
            raise e

    return APIResponse(response=response, is_cache=is_cache, last_cache_time=user.cache.get("time", "недавно"))


async def get_schedule_item(
        user: User,
        apis: APIs,
        lesson_id: int,
):
    return await apis.mobile.get_lesson_schedule_item(
        profile_id=user.db_profile_id,
        student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
        lesson_id=lesson_id
    ) if user.system == Texts.Systems.MY_SCHOOL else await apis.mobile.get_lesson_schedule_item(
        profile_id=user.db_profile_id,
        student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
        lesson_id=lesson_id
    )


async def get_subjects_marks(
        user: User,
        apis: APIs,
) -> APIResponse[types.mobile.SubjectsMarks]:
    is_cache = False
    try:
        response = await apis.mobile.get_subjects_marks(
            student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
            profile_id=user.db_profile_id
        )
    except Exception as e:
        logging.error("API-Exception", exc_info=e)
        if user.cache.get("marks", {}).get("by_subject", None):
            response = types.mobile.SubjectsMarks.model_validate(
                user.cache["marks"]["by_subject"]
            )
            is_cache = True
        else:
            raise e

    return APIResponse(response=response, is_cache=is_cache, last_cache_time=user.cache.get("time", "недавно"))


class RatingType(enum.Enum):
    CLASS = "class"
    SUBJECTS = "subjects"
    SHORT = "short"


async def get_rating(
        user: User,
        apis: APIs,
        type: RatingType = RatingType.CLASS,
        date: Optional[date] = None,
        end_date: Optional[date] = None
) -> APIResponse[list[types.mobile.RatingRankClass]] | APIResponse[list[types.mobile.RatingRankSubject]] | APIResponse[list[types.mobile.RatingRankShort]]:
    is_cache = False

    try:
        response = (
            await apis.mobile.get_rating_rank_class(
                person_id=user.db_current_child["contingent_guid"] if user.db_current_child else user.db_profile["children"][0]["contingent_guid"],
                profile_id=user.db_profile_id,
                date=date or get_date(),
                class_unit_id=user.db_current_child["class_unit_id"] if user.db_current_child else user.db_profile["children"][0]["class_unit_id"]
            )
            if type == RatingType.CLASS
            else await apis.mobile.get_rating_rank_subjects(
                person_id=user.db_current_child["contingent_guid"] if user.db_current_child else user.db_profile["children"][0]["contingent_guid"],
                profile_id=user.db_profile_id, date=date or get_date()
            ) if type == RatingType.SUBJECTS
            else await apis.mobile.get_rating_rank_short(
                person_id=user.db_current_child["contingent_guid"] if user.db_current_child else user.db_profile["children"][0]["contingent_guid"],
                profile_id=user.db_profile_id,
                begin_date=date or get_date(),
                end_date=end_date or get_date()
            )
        )
    except Exception as e:
        logging.error("API-Exception", exc_info=e)
        if user.cache.get("rating", {}).get(type.value, None):
            is_cache = True
            if type == RatingType.CLASS:
                response = types.mobile.RatingRankClass.model_validate(user.cache["rating"]["class"])
            elif type == RatingType.SUBJECTS:
                response = types.mobile.RatingRankSubject.model_validate(user.cache["rating"]["subjects"])
            else:
                response = types.mobile.RatingRankShort.model_validate(user.cache["rating"]["short"])
        else:
            raise e

    return APIResponse(response=response, is_cache=is_cache, last_cache_time=user.cache.get("time", "недавно"))


async def get_class_members(user: User, apis: APIs) -> APIResponse[types.mobile.ClassMembers]:
    is_cache = False

    try:
        response = await apis.mobile.get_class_members(
            class_unit_id=user.db_current_child["class_unit_id"] if user.db_current_child else user.db_profile["children"][0]["class_unit_id"]
        )
    except Exception as e:
        logging.error("API-Exception", exc_info=e)
        if user.cache.get("class_members", None):
            is_cache = True
            response = types.mobile.ClassMembers.model_validate(user.cache["class_members"])
        else:
            raise e

    return APIResponse(response=response, is_cache=is_cache, last_cache_time=user.cache.get("time", "недавно"))


async def get_mark(
        user: User,
        apis: APIs,
        mark_id: str,
) -> APIResponse[MarkInfo]:
    return APIResponse[MarkInfo](
        response=(
            await apis.mobile.request(
                method="GET",
                base_url=BaseURL(type=URLTypes.SCHOOL_API, system=user.system),
                path=f"/family/mobile/v1/marks/{mark_id}",
                params={
                    "student_id": (
                        user.db_current_child["id"]
                        if user.db_current_child
                        else user.db_profile["children"][0]["id"]
                    ),
                },
                custom_headers={
                    "x-mes-subsystem": "familymp",
                    "client-type": "diary-mobile",
                    "profile-id": user.db_profile_id,
                },
                model=MarkInfo
            )
        )
    )