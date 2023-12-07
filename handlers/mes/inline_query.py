#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import date, timedelta
from re import Match

from aiogram import Bot, F
from aiogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
)

from database import User
from handlers.mes.homeworks import homeworks_info, homeworks_past, homeworks_upcoming
from handlers.mes.marks import marks_sorted_by_date_info, marks_sorted_by_subject_info, marks_by_date, marks_by_subject
from handlers.mes.profile import profile_info, profile_cmd
from handlers.mes.router import APIs, Mes, MesUser, isMesUser, router
from handlers.mes.schedule import day_schedule_info, lesson_info, schedule, get_lesson_info
from handlers.mes.settings import TEXT, markup
from octodiary.exceptions import APIError
from octodiary.types.mes.mobile import FamilyProfile
from handlers.mes.visits import visits_info
from inline.types import AdditionalButtons
from utils.other import handler, sort_dict_by_date
from utils.texts import Texts


@router.inline_query(
    F.func(isMesUser),
    F.func(MesUser),
    F.func(Mes),
    F.query.strip() == ""
)
@handler()
async def inline_query(update: InlineQuery):
    return await update.answer(
        [
            InlineQueryResultArticle(
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=Texts.CLICK_TO_LOAD,
                                callback_data=result_info["id"]
                            )
                        ]
                    ]
                ),
                input_message_content=InputTextMessageContent(
                    message_text=Texts.INLINE_MESSAGE_TEXT
                ),
                **result_info
            )
            for result_info in Texts.Mes.Inline.values()
        ],
        cache_time=15,
        is_personal=True,
        button=InlineQueryResultsButton(
            **Texts.INLINE_QUERY_RESULTS_BUTTON
        )
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.SCHEDULE.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.SCHEDULE.id
)
@handler()
async def schedule_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    from_db = ""
    try:
        today = date.today()
        events = await apis.mobile.get_events(
            person_id=user.db_profile["children"][0]["contingent_guid"],
            mes_role=user.db_profile["profile"]["type"],
            begin_date=(
                today - timedelta(days= -1*(0 - today.weekday()))
            ),
            end_date=(
                today + timedelta(days=14+(6 - today.weekday()))
            )
        )
    except APIError:
        events = user.db_events
        from_db = Texts.FROM_DB

    await bot.inline.list(
        update,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": schedule,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(
            dictionary=day_schedule_info(events, from_db, inline=True)
        ),
        row_width=5
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.PROFILE.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.PROFILE.id
)
@handler()
async def profile_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    from_db = ""
    try:
        profile = await apis.mobile.get_family_profile(user.db_profile_id)
    except APIError:
        profile = FamilyProfile.model_validate(user.db_profile)
        from_db = Texts.FROM_DB

    await bot.edit_message_text(
        text=await profile_info(profile, from_db, apis, user),
        inline_message_id=update.inline_message_id,
        reply_markup=bot.inline.generate_markup(
            {
                "text": Texts.Buttons.UPDATE,
                "callback": profile_cmd,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        )
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.HOMEWORKS_UPCOMING.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.HOMEWORKS_UPCOMING.id
)
@handler()
async def homeworks_upcoming_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today(),
        to_date=(date.today() + timedelta(days=14))
    )

    await bot.inline.list(
        update=update,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": homeworks_upcoming,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(homeworks_info(homeworks)),
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.HOMEWORKS_PAST.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.HOMEWORKS_PAST.id
)
@handler()
async def homeworks_past_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    homeworks = await apis.mobile.get_homeworks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today() - timedelta(days=14),
        to_date=date.today() - timedelta(days=1)
    )

    await bot.inline.list(
        update=update,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": homeworks_past,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(homeworks_info(homeworks), reverse=True),
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.MARKS_BY_DATE.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.MARKS_BY_DATE.id
)
@handler()
async def marks_by_date_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    marks = await apis.mobile.get_marks(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id,
        from_date=date.today() - timedelta(days=14),
        to_date=date.today(),
    )

    await bot.inline.list(
        update=update,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": marks_by_date,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(marks_sorted_by_date_info(marks), reverse=True),
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.MARKS_BY_SUBJECT.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.MARKS_BY_SUBJECT.id
)
@handler()
async def marks_by_subject_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    marks = await apis.mobile.get_subject_marks_short(
        student_id=user.db_profile["children"][0]["id"],
        profile_id=user.db_profile_id
    )

    await bot.inline.list(
        update=update,
        row_width=2,
        strings=marks_sorted_by_subject_info(
            marks,
            user.db_settings.get("goals", False)
        ),
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": marks_by_subject,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.SETTINGS.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.SETTINGS.id
)
@handler()
async def settings_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    await bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis)
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id == Texts.Mes.Inline.VISITS.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data == Texts.Mes.Inline.VISITS.id
)
@handler()
async def visits_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs):
    try:
        today = date.today()
        visits = await apis.mobile.get_visits(
            profile_id=user.db_profile_id,
            student_id=user.db_profile["children"][0]["id"],
            contract_id=user.db_profile["children"][0]["contract_id"],
            from_date=today - timedelta(days=14),
            to_date=today,
        )
    except APIError as e:
        await bot.edit_message_text(
            Texts.API_ERROR(ERROR=e),
            inline_message_id=update.inline_message_id
        )
        return

    await bot.edit_message_text(
        visits_info(visits),
        inline_message_id=update.inline_message_id,
        reply_markup=bot.inline.generate_markup(
            {
                "text": Texts.Buttons.UPDATE,
                "callback": visits,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        )
    )


@router.inline_query(
    F.func(isMesUser),
    F.func(MesUser),
    F.func(Mes),
    F.query.strip().regexp(r"lesson (.*[0-9])").as_("match")
)
@handler()
async def lesson_info_inline_query(update: InlineQuery, match: Match):
    lesson_id = match.group(1)

    return await update.answer(
        [
            InlineQueryResultArticle(
                id=Texts.InlineQueryLessonInfo.ID(LESSON_ID=lesson_id),
                title=Texts.InlineQueryLessonInfo.TITLE,
                description=Texts.InlineQueryLessonInfo.DESCRIPTION(LESSON_ID=lesson_id),
                thumbnail_url=Texts.InlineQueryLessonInfo.THUMBNAIL_URL,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=Texts.CLICK_TO_LOAD,
                                callback_data=Texts.InlineQueryLessonInfo.ID(LESSON_ID=lesson_id)
                            )
                        ]
                    ]
                ),
                input_message_content=InputTextMessageContent(
                    message_text=Texts.INLINE_MESSAGE_TEXT
                ),
            )
        ],
        cache_time=10,
        is_personal=True,
        button=InlineQueryResultsButton(
            **Texts.INLINE_QUERY_RESULTS_BUTTON
        )
    )


@router.chosen_inline_result(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.result_id.regexp(r"lesson:(.*[0-9])").as_("match"),
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.func(isMesUser),
    F.func(MesUser).as_("user"),
    F.func(Mes).as_("apis"),
    F.data.regexp(r"lesson:(.*[0-9])").as_("match")
)
@handler()
async def lesson_info_load(update: ChosenInlineResult, bot: Bot, user: User, apis: APIs, match: Match):
    try:
        lesson = await apis.mobile.get_schedule_item(
            profile_id=user.db_profile_id,
            student_id=user.db_profile["children"][0]["id"],
            lesson_id=match.group(1)
        )
    except APIError as e:
        await bot.edit_message_text(
            text=Texts.API_ERROR(ERROR=e),
            inline_message_id=update.inline_message_id
        )
        return

    return await bot.edit_message_text(
        text=lesson_info(lesson),
        inline_message_id=update.inline_message_id,
        reply_markup=bot.inline.generate_markup(
            {
                "text": Texts.Buttons.UPDATE,
                "callback": get_lesson_info,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "lesson_id": match.group(1),
                    "is_inline": True
                },
                "reusable": True,
                "disable_deadline": True
            }
        )
    )
