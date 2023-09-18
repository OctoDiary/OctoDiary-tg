from datetime import date, timedelta

from aiogram import F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ChosenInlineResult, InlineQuery, Message, ReplyKeyboardRemove
from database import User
from octodiary.exceptions import APIError
from octodiary.types.myschool.mobile import ShortHomeworks
from utils import keyboard

from .router import APIs, MySchool, MySchoolUser, router


class HomeworksState(StatesGroup):
    type = State()

def homeworks_info(homeworks: ShortHomeworks):
    days = {}
    for homework in homeworks.payload:
        if (date_str := homework.date.strftime("%d.%m")) not in days:
            days[date_str] = {}
        
        if homework.subject_name not in days[date_str]:
            days[date_str][homework.subject_name] = []
        
        days[date_str][homework.subject_name] += [f"<code>{homework.description}</code>"]
    
    return {
        date_str: f"📝 <b>Домашние задания на {date_str}:</b>\n\n" + "\n".join([
            f"• <b>{subject}</b>"
            + (
                ("\n   ├ " if len(homeworks) > 1 else "")
                + "\n   ├ ".join(homeworks[:-1])
                + f"\n   └ {homeworks[-1]}"
            )
            for subject, homeworks in subjects.items()
        ])
        for date_str, subjects in days.items()
    }


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    Command("homeworks")
)
@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    F.text == "Домашние задания",
    F.chat.type == ChatType.PRIVATE
)
async def homeworks(message: Message, apis: APIs, user: User, state: FSMContext):
    """Домашние задания (ДЗ)"""

    await state.set_state(HomeworksState.type)
    await message.answer(
        "❔ Какие <b>ДЗ</b> вы хотите <b>просмотреть</b>?",
        reply_markup=keyboard.HOMEWORKS_TYPE
    )


@router.message(
    F.func(MySchoolUser).as_("user"),
    F.func(MySchool).as_("apis"),
    HomeworksState.type,
)
async def get_homeworks(message: Message, apis: APIs, user: User, state: FSMContext):
    """Домашние задания (ДЗ)"""

    await state.clear()
    upcoming = message.text == "Ближайшие"

    try:
        homeworks = await apis.mobile.get_homeworks_short(
            student_id=user.db_profile["children"][0]["id"],
            profile_id=user.db_profile_id,
            from_date=date(2023, 9, 1) if not upcoming else date.today(),
            to_date=(date.today() + timedelta(days=7)) if upcoming else date.today() - timedelta(days=1)
        )
    except APIError as e:
        return await message.answer(f"❕ [<code>{e.status_code}</code>] Сервер <b>не ответил</b> на запрос, <b>ошибка</b>...\nПопробуйте позднее.")
    
    
    await message.bot.inline.list(
        update=message,
        strings=homeworks_info(homeworks),
    )
    await (await message.answer("...", reply_markup=keyboard.DEFAULT)).delete()