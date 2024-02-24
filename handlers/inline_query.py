#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import timedelta
from re import Match

from aiogram import F
from aiogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
)

import api
from apis import APIs
from database import User
from handlers.homeworks import homeworks_info, homeworks_past, homeworks_upcoming
from handlers.marks import marks_by_date, marks_by_subject, marks_sorted_by_date_info, marks_sorted_by_subject_info
from handlers.profile import profile_cmd, profile_info
from handlers.router import router
from handlers.schedule import day_schedule_info, get_lesson_info, lesson_info, schedule
from handlers.settings import TEXT, markup
from handlers.visits import visits_cmd, visits_info
from inline.types import AdditionalButtons
from octodiary.exceptions import APIError
from utils.filters import apis_and_user
from utils.other import get_date, handler, sort_dict_by_date
from utils.texts import Texts


@router.inline_query(
    F.query.strip() == ""
)
@handler()
@apis_and_user
async def inline_query(update: InlineQuery, apis: APIs, user: User):
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
            for result_info in (Texts.Mes if user.system == Texts.Systems.MES else Texts.MySchool).Inline.values()
        ],
        cache_time=15,
        is_personal=True,
        button=InlineQueryResultsButton(
            **Texts.INLINE_QUERY_RESULTS_BUTTON
        )
    )


@router.chosen_inline_result(
    F.result_id == Texts.Mes.Inline.SCHEDULE.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(F.data == Texts.Mes.Inline.SCHEDULE.id)
@handler()
@apis_and_user
async def schedule_load(update: ChosenInlineResult, user: User, apis: APIs):
    today = get_date()
    events_response = await api.get_events(
        user=user,
        apis=apis,
        begin_date=(today - timedelta(days=-1 * (0 - today.weekday()))),
        end_date=(today + timedelta(days=14 + (6 - today.weekday())))
    )

    await update.bot.inline.list(
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
            dictionary=day_schedule_info(events_response, inline=True)
        ),
        row_width=5
    )


@router.chosen_inline_result(
    F.result_id == Texts.Mes.Inline.PROFILE.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data == Texts.Mes.Inline.PROFILE.id
)
@handler()
@apis_and_user
async def profile_load(update: ChosenInlineResult, user: User, apis: APIs):
    profile = await api.get_profile(user=user, apis=apis)

    await update.bot.edit_message_text(
        text=await profile_info(profile, apis, user),
        inline_message_id=update.inline_message_id,
        reply_markup=update.bot.inline.generate_markup(
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
    F.result_id == Texts.Mes.Inline.HOMEWORKS_UPCOMING.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data == Texts.Mes.Inline.HOMEWORKS_UPCOMING.id
)
@handler()
@apis_and_user
async def homeworks_upcoming_load(update: ChosenInlineResult, user: User, apis: APIs):
    homeworks = await api.get_homeworks(
        user=user,
        apis=apis,
        type=api.HomeworkTypes.UPCOMING
    )

    await update.bot.inline.list(
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
    F.result_id == Texts.Mes.Inline.HOMEWORKS_PAST.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data == Texts.Mes.Inline.HOMEWORKS_PAST.id
)
@handler()
@apis_and_user
async def homeworks_past_load(update: ChosenInlineResult, user: User, apis: APIs):
    homeworks = await api.get_homeworks(
        user=user,
        apis=apis,
        type=api.HomeworkTypes.PAST
    )

    await update.bot.inline.list(
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
    F.result_id == Texts.Mes.Inline.MARKS_BY_DATE.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data == Texts.Mes.Inline.MARKS_BY_DATE.id
)
@handler()
@apis_and_user
async def marks_by_date_load(update: ChosenInlineResult, user: User, apis: APIs):
    marks = await api.get_marks(
        user=user,
        apis=apis,
        from_date=get_date() - timedelta(days=14),
        to_date=get_date(),
    )

    await update.bot.inline.list(
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
    F.result_id == Texts.Mes.Inline.MARKS_BY_SUBJECT.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data == Texts.Mes.Inline.MARKS_BY_SUBJECT.id
)
@handler()
@apis_and_user
async def marks_by_subject_load(update: ChosenInlineResult, user: User, apis: APIs):
    marks = await api.get_subjects_marks(user, apis)

    await update.bot.inline.list(
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
    F.result_id == Texts.Mes.Inline.SETTINGS.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data == Texts.Mes.Inline.SETTINGS.id
)
@handler()
@apis_and_user
async def settings_load(update: ChosenInlineResult, user: User, apis: APIs):
    await update.bot.inline.answer(
        update=update,
        response=TEXT,
        reply_markup=markup(user, apis)
    )


@router.chosen_inline_result(
    F.result_id == Texts.Mes.Inline.VISITS.id,
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data == Texts.Mes.Inline.VISITS.id
)
@handler()
@apis_and_user
async def visits_load(update: ChosenInlineResult, user: User, apis: APIs):
    bot = update.bot

    try:
        today = get_date()
        visits_data = await apis.mobile.get_visits(
            profile_id=user.db_profile_id,
            student_id=user.db_current_child["id"] if user.db_current_child else user.db_profile["children"][0]["id"],
            contract_id=user.db_current_child["contract_id"] if user.db_current_child else user.db_profile["children"][0]["contract_id"],
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
        visits_info(visits_data),
        inline_message_id=update.inline_message_id,
        reply_markup=bot.inline.generate_markup(
            {
                "text": Texts.Buttons.UPDATE,
                "callback": visits_cmd,
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
    F.result_id.regexp(r"lesson:(.*[0-9])").as_("match"),
    F.inline_message_id.func(lambda inline_message_id: inline_message_id is not None)
)
@router.callback_query(
    F.data.regexp(r"lesson:(.*[0-9])").as_("match")
)
@handler()
@apis_and_user
async def lesson_info_load(update: ChosenInlineResult, user: User, apis: APIs, match: Match):
    try:
        lesson = await api.get_schedule_item(
            user=user, apis=apis,
            lesson_id=match.group(1)
        )
    except APIError as e:
        await update.bot.edit_message_text(
            text=Texts.API_ERROR(ERROR=e),
            inline_message_id=update.inline_message_id
        )
        return

    return await update.bot.edit_message_text(
        text=lesson_info(lesson),
        inline_message_id=update.inline_message_id,
        reply_markup=update. bot.inline.generate_markup(
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
