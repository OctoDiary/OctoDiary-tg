#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import enum
from datetime import date, timedelta, datetime, timezone

from database import User
from apis import MesAPIs, MySchoolAPIs
from octodiary import exceptions, types
from utils import Texts
from utils.other import get_date
from typing import Optional


class HomeworkTypes(enum.Enum):
    UPCOMING = 1
    PAST = 2


async def get_homeworks(
        user: User,
        apis: MesAPIs | MySchoolAPIs,
        type: HomeworkTypes
) -> types.mes.mobile.ShortHomeworks | types.myschool.mobile.ShortHomeworks:
    return await apis.mobile.get_homeworks_short(
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


async def get_events(
        user: User,
        apis: MesAPIs | MySchoolAPIs,
        begin_date: date,
        end_date: date,
        *,
        profile: types.mes.mobile.FamilyProfile | types.myschool.mobile.FamilyProfile | dict = None
) -> types.mes.mobile.EventsResponse | types.myschool.mobile.EventsResponse:
    if profile is None:
        profile = user.db_profile

    if not isinstance(profile, dict):
        profile = profile.model_dump()

    return await apis.mobile.get_events(
        person_id=user.db_current_child["contingent_guid"] if user.db_current_child else profile["children"][0]["contingent_guid"],
        mes_role=profile["profile"]["type"],
        begin_date=begin_date,
        end_date=end_date
    )


async def get_profile_users_info(user: User, apis: MesAPIs | MySchoolAPIs):
    match user.system:
        case Texts.Systems.MY_SCHOOL:
            return await apis.mobile.get_users_profile_info()
        case Texts.Systems.MES:
            return await apis.mobile.get_users_profiles_info()


async def get_profile(
        user: User,
        apis: MesAPIs | MySchoolAPIs,
        profile_id: Optional[int] = None
) -> types.mes.mobile.FamilyProfile | types.myschool.mobile.FamilyProfile:
    match user.system:
        case Texts.Systems.MY_SCHOOL:
            return await apis.mobile.get_profile(profile_id=profile_id or user.db_profile_id)
        case Texts.Systems.MES:
            return await apis.mobile.get_family_profile(profile_id=profile_id or user.db_profile_id)


async def get_marks(
        user: User,
        apis: MesAPIs | MySchoolAPIs,
        from_date: datetime.date,
        to_date: datetime.date,
        *,
        student_id: Optional[int] = None
) -> types.mes.mobile.Marks | types.myschool.mobile.Marks:
    return await apis.mobile.get_marks(
        student_id=student_id or user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=from_date,
        to_date=to_date
    )


async def get_schedule_item(
        user: User,
        apis: MesAPIs | MySchoolAPIs,
        lesson_id: int,
):
    return await apis.mobile.get_lesson_schedule_items(
        profile_id=user.db_profile_id,
        student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
        lesson_id=lesson_id
    ) if user.system == Texts.Systems.MY_SCHOOL else await apis.mobile.get_schedule_item(
        profile_id=user.db_profile_id,
        student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
        lesson_id=lesson_id
    )


async def get_short_marks(
        user: User,
        apis: MesAPIs | MySchoolAPIs,
) -> types.mes.mobile.short_subject_marks.ShortSubjectMarks | types.myschool.mobile.short_subject_marks.ShortSubjectMarks:
    return await apis.mobile.get_subject_marks_short(
        student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id
    )
