#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import re
from datetime import timedelta
from typing import Optional

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from pydantic import BaseModel

import api
from apis import APIs
from database import Database, User
from handlers.router import router
from inline.types import AdditionalButtons
from octodiary.types.mobile import SubjectsMarks
from octodiary.types.mobile.marks import Marks
from octodiary.types.mobile.marks import Payload as MarkPayloadItem
from octodiary.types.mobile.subject_marks import Payload
from utils.filters import apis_and_user, is_authorized, user_apis
from utils.other import get_date, handler, pluralization_string, sort_dict_by_date
from utils.other import mark as MARK
from utils.texts import Texts


def mark_info(mark: MarkPayloadItem):
    return Texts.MARK_INFO(
        SUBJECT_NAME=mark.subject_name,
        MARK=MARK(mark.value, mark.weight),
        CONTROL_FORM_NAME=mark.control_form_name,
        WEIGHT=pluralization_string(mark.weight, ["балл", "балла", "баллов"]),
        IS_EXAM_EMOJI="❗️" if mark.is_exam else "",
        UPDATED_AT=mark.updated_at.replace("T", " ")[:-3],
        COMMENT=mark.comment or "❌"
    )


def marks_sorted_by_date_info(marks_data: api.APIResponse[Marks]):
    marks = marks_data.response
    days = {}
    for mark in marks.payload:
        if (date_str := ".".join(str(mark.date)[5:10].split("-")[::-1])) not in days:
            days[date_str] = {}

        if mark.subject_name not in days[date_str]:
            days[date_str][mark.subject_name] = []

        days[date_str][mark.subject_name] += [mark_info(mark)]

    return {
        date_str: (Texts.FROM_CACHE(marks_data.last_cache_time) if marks_data.is_cache else "") + Texts.MARKS_FOR_DATE(DATE=date_str) + "\n\n".join([
            "\n".join(marks)
            for subject, marks in subjects.items()
        ])
        for date_str, subjects in days.items()
    }


def dynamic(item):
    return "🔺" if item.dynamic == "UP" else "🔻" if item.dynamic == "DOWN" else ""


def marks_subject_item(item: Payload, *, allow_goals: bool = False):
    text = Texts.SUBJECT_MARKS_INFO(
        SUBJECT_NAME=item.subject_name,
        AVERAGE_BY_ALL=item.average_by_all
    )

    periods = [
        Texts.SUBJECT_MARKS_PERIOD_INFO(
            TITLE=period.title,
            START=period.start,
            END=period.end,
            AVERAGE=period.value or "❌",
            DYNAMIC=dynamic(period) if not period.fixed_value else "",
            GOALS=(
                    Texts.GOAL(
                        ROUND=period.target.round,
                        VALUE=period.target.value
                    ) + Texts.OR.join([
                        MARK(str(method.value), method.weight) + f"[{method.remain} шт.]"
                        for method in period.target.paths
                    ]) + "</code>\n"
            ) if allow_goals and period.target and period.target.round and period.target.paths else "",
            FIXED_VALUE=period.fixed_value or "❌",
            COUNT=str(period.count or "❌"),
            MARKS=(
                "; ".join([
                    MARK(mark.value, mark.weight)
                    for mark in period.marks
                ]) if period.marks else "❌"
            )
        )
        for period in item.periods
    ]

    text += "\n" + "".join(periods)

    return text


def marks_sorted_by_subject_info(marks_short: api.APIResponse[SubjectsMarks], goals: bool = False) -> dict[str, str]:
    return {
        (
            item
            .subject_name
            .replace(Texts.OBZ, Texts.OBZ_SHORT)
            .replace(Texts.PHIZ_KULTURA, Texts.PHIZ_KULTURA_SHORT)
        ): info
        for item in marks_short.response.payload
        if (info := marks_subject_item(item=item, allow_goals=goals))
    }


@router.message(Command("marks_by_date"))
@router.message(F.text == Texts.Buttons.MARKS_BY_DATE, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def marks_by_date(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        *,
        is_inline: bool = False
):
    """Marks users by date"""

    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    marks = await api.get_marks(
        user=user,
        apis=apis,
        from_date=get_date() - timedelta(days=14),
        to_date=get_date(),
    )

    await update.bot.inline.list(
        update=response,
        row_width=5,
        additional_buttons=AdditionalButtons(
            below_buttons={
                "text": Texts.Buttons.UPDATE,
                "callback": marks_by_date,
                "kwargs": {
                    "apis": apis,
                    "user": user,
                    "is_inline": is_inline
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
        **sort_dict_by_date(marks_sorted_by_date_info(marks), reverse=True)
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)


@router.message(Command("marks_by_subject"))
@router.message(F.text == Texts.Buttons.MARKS_BY_SUBJECT, F.chat.type == ChatType.PRIVATE)
@handler()
@apis_and_user
async def marks_by_subject(
        update: Message | CallbackQuery,
        apis: APIs,
        user: User,
        *,
        is_inline: bool = False
):
    """Marks users by subject"""

    if not is_inline:
        response = await update.bot.inline.answer(update, Texts.LOADING)
    else:
        response = update

    marks = await api.get_subjects_marks(user=user, apis=apis)

    await update.bot.inline.list(
        update=response,
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
                    "is_inline": is_inline
                },
                "reusable": True,
                "disable_deadline": True
            }
        ),
    )

    if isinstance(update, CallbackQuery):
        await update.answer(Texts.UPDATED)


class Mark(BaseModel):
    value: int
    weight: int


class CalculatorWeightedAverageMarks:
    def __init__(self, marks: Optional[list[Mark]] = None):
        self.marks = marks or []

    def add_mark(self, value: int, weight: int):
        self.marks.append(Mark(value=value, weight=weight))

        return self.calculate()

    def calculate(self):
        return sum([mark.value * mark.weight for mark in self.marks]) / sum([mark.weight for mark in self.marks]) if self.marks else 0


class Calculator(StatesGroup):
    SUBJECT = State()
    PERIOD = State()
    MARK = State()


@router.message(Command("calc", "calculate", "calculator"))
@router.message(F.text == Texts.Buttons.CALCULATOR, F.chat.type == ChatType.PRIVATE)
@handler()
async def calculator(
    message: Message,
    state: FSMContext
):
    """Calculator for marks :: main"""

    if not is_authorized(message.from_user):
        await state.set_state(Calculator.MARK)
        await state.update_data(subject=None, period=None, average=CalculatorWeightedAverageMarks())
        await message.answer(Texts.Calculator.ENTER_MARKS)
        return

    user = Database().user(message.from_user.id)
    apis = user_apis(user)

    marks_info = await api.get_subjects_marks(user=user, apis=apis)

    data = {
        i.subject_name: {
            p.title: [Mark(value=int(m.value), weight=m.weight) for m in p.marks]
            for p in i.periods
        }
        for i in marks_info.response.payload
    }
    await state.update_data(data=data)

    await message.answer(Texts.Calculator.CHOOSE_SUBJECT, reply_markup=ReplyKeyboardMarkup(
        keyboard=[*message.bot.inline.chunks([KeyboardButton(text=subject) for subject in data], 2), [KeyboardButton(text=Texts.Buttons.WITH_NULL)]],
        resize_keyboard=True
    ))
    await state.set_state(Calculator.SUBJECT)


@router.message(Calculator.SUBJECT)
@handler()
async def calculator_subject(
    message: Message,
    state: FSMContext
):
    """Calculator for marks :: subject"""
    state_data = await state.get_data()
    if message.text == Texts.Buttons.WITH_NULL:
        await state.set_state(Calculator.MARK)
        await state.update_data(subject=None, period=None, average=CalculatorWeightedAverageMarks())
        await message.answer(Texts.Calculator.ENTER_MARKS, reply_markup=ReplyKeyboardRemove())
        return

    if message.text not in state_data and message.text != Texts.Buttons.WITH_NULL:
        return

    await state.update_data(subject=message.text)

    await message.answer(Texts.Calculator.CHOOSE_PERIOD, reply_markup=ReplyKeyboardMarkup(
        keyboard=message.bot.inline.chunks([KeyboardButton(text=period) for period in state_data[message.text]], 2),
        resize_keyboard=True
    ))
    await state.set_state(Calculator.PERIOD)


@router.message(Calculator.PERIOD)
@handler()
async def calculator_period(
    message: Message,
    state: FSMContext
):
    """Calculator for marks :: period"""
    state_data = await state.get_data()
    if message.text not in state_data[state_data["subject"]]:
        return

    marks = state_data[state_data["subject"]][message.text]

    await state.update_data(
        period=message.text,
        marks=marks,
        average=CalculatorWeightedAverageMarks(marks)
    )

    await message.answer(Texts.Calculator.ENTER_MARKS, reply_markup=ReplyKeyboardRemove())
    await message.answer(
        Texts.Calculator.AVERAGE.format(
            AVERAGE=(await state.get_data())["average"].calculate(),
            ALL=" ".join([
                MARK(mark.value, mark.weight)
                for mark in (await state.get_data())["average"].marks
            ])
        )
    )
    await state.set_state(Calculator.MARK)


@router.message(Calculator.MARK)
@handler()
async def calculator_mark(
    message: Message,
    state: FSMContext
):
    """Calculator for marks :: mark"""
    state_data = await state.get_data()
    if message.text == "-last":
        state_data["average"].marks.remove(state_data["average"].marks[-1])
        new_average = state_data["average"].calculate()
    else:
        if not (match := re.match(r"(\d+) (\d+)", message.text)) or int(match.group(2)) > 9 or int(match.group(2)) < 1 or int(match.group(1)) < 1:
            return await message.answer(Texts.Calculator.INVALID_MARK)

        new_average = state_data["average"].add_mark(int(match.group(1)), int(match.group(2)))

    await message.answer(
        Texts.Calculator.AVERAGE.format(
            AVERAGE=new_average,
            ALL=" ".join([
                MARK(mark.value, mark.weight)
                for mark in state_data["average"].marks
            ])
        )
    )
