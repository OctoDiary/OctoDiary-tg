#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary
import asyncio
import contextlib
import os
from datetime import date, timedelta

import requests
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BufferedInputFile, InputMediaPhoto, CallbackQuery, ReactionTypeEmoji

from core.misc.texts import Texts
from core.misc.utils import get_date, pluralization_string
from core.services.database import database

import plotly.graph_objs as go


AdminFilter = F.func(lambda message: message.from_user.id in database.admins)
router = Router(name="Admins")


def generate_figure(
    keys: list[str],
    start_date: date,
    end_date: date,
    values_mes: list[int],
    values_my_school: list[int]
):
    fig = go.Figure(data=[
        go.Scatter(x=keys, y=values_mes, name="МЭШ", mode='lines+markers'),
        go.Scatter(x=keys, y=values_my_school, name="Моя Школа", mode="lines+markers")
    ])
    fig.update_layout(
        title=f"Посещения OctoDiary с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}",
        title_x=0.5,
        yaxis_title="Кол-во",
        legend=dict(x=.5, xanchor="center", orientation="h"),
        margin=dict(l=0, r=0, t=30, b=0)
    )

    return fig.to_image(format="png", scale=3)


def generate_histograms(
    data: list[dict]
):
    mes = {}
    my_school = {}

    for user in data:
        if "system" not in user:
            continue

        ss = user["system"]

        for j, k in user.items():
            if j != "system":
                match ss:
                    case 0:
                        mes[j] = mes.get(j, 0) + k
                    case 1:
                        my_school[j] = my_school.get(j, 0) + k

    today = get_date()
    one_week_days = [today] + [
        today - timedelta(days=i)
        for i in range(7)
    ]
    one_week_days.reverse()

    two_week_days = [today - timedelta(days=7)] + [
        today - timedelta(days=i)
        for i in range(7, 15)
    ]
    two_week_days.reverse()

    keys_one = [f'{i.year}-{i.month}-{i.day}' for i in one_week_days]
    keys_two = [f'{i.year}-{i.month}-{i.day}' for i in two_week_days]

    return [
        generate_figure(
            keys=keys_one, start_date=one_week_days[0], end_date=one_week_days[-1],
            values_mes=[mes.get(i, 0) for i in keys_one],
            values_my_school=[my_school.get(i, 0) for i in keys_one]
        ),
        generate_figure(
            keys=keys_two, start_date=two_week_days[0], end_date=two_week_days[-1],
            values_mes=[mes.get(i, 0) for i in keys_two],
            values_my_school=[my_school.get(i, 0) for i in keys_two]
        )
    ]


@router.message(Command("statistics"), AdminFilter)
async def statistics(message: Message):
    m = await message.answer("Генерация графиков...")

    app_stats = requests.get(
        f"{'https://den4iksop.org' if not os.environ.get('TEST') else 'http://localhost:1811'}/octodiary/stats",
        headers={
            "verify-token": os.environ.get("STATES_TOKEN")
        }
    ).json()

    await message.answer_media_group([
        InputMediaPhoto(
            media=BufferedInputFile(x, filename="plot.png"),
            show_caption_above_media=True,
            caption=Texts.Admin.STATISTICS(
                len([
                    user_id
                    for user_id in database.keys()
                    if user_id.isdigit() and database.user(user_id).system
                ]),
                database.settings.get(f"new-users-month:{date.today().month}", 0),
                pluralization_string(len([
                    user
                    for user in app_stats.values()
                    if user.get("system", None) == 0
                ]), ["пользователь", "пользователя", "пользователей"]),
                pluralization_string(app_stats["stats-system"]["0"], ["посещение", "посещения", "посещений"]),
                pluralization_string(len([
                    user
                    for user in app_stats.values()
                    if user.get("system", None) == 1
                ]), ["пользователь", "пользователя", "пользователей"]),
                pluralization_string(app_stats["stats-system"]["1"], ["посещение", "посещения", "посещений"]),
            ) if i == 0 else None
        )
        for i, x in enumerate(generate_histograms(list(app_stats.values())))
    ])
    await m.delete()


@router.message(Command("notify"), AdminFilter)
async def notify(message: Message, command: CommandObject):
    if not message.reply_to_message:
        await message.answer(text=Texts.Admin.NOTIFY_NO_REPLY)
        return

    await message.bot.inline.answer(  # noqa
        message,
        response=Texts.NOTIFY_CONFIRM,
        reply_markup=[
            {
                "text": Texts.Buttons.OK,
                "callback": start_notify,
                "kwargs": {
                    "message": message,
                    "command": command
                }
            },
            {
                "text": Texts.Buttons.CANCEL,
                "callback": delete
            }
        ]
    )


async def delete(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()


async def start_notify(callback: CallbackQuery, message, command: CommandObject):
    args = (command.args or "").split(" ")
    system = ""
    delete_users = False
    users_ids = []

    for arg in args:
        if arg in ["-s", "--system"]:
            system = args[args.index(arg) + 1]
        elif arg in ["-du", "--delete-users"]:
            delete_users = True
        elif arg in ["-u", "--users"]:
            users_ids_raw = args[args.index(arg) + 1]
            users_ids = [int(user_id) for user_id in users_ids_raw.split(",")]
        elif arg in ["-na", "--not-authorized"]:
            users_ids = [
                user_id
                for user_id in database.settings.get("full-users-ids", [])
                if user_id not in database.keys()
                or not database.user(user_id).token
            ]

    _message = await callback.message.edit_text(
        text=Texts.Admin.NOTIFY_SENDING
    )

    notification_message = message.reply_to_message
    successfully_sent = 0
    for user in [
        int(user_id)
        for user_id in database.keys()
        if user_id.isdigit() and database.user(user_id).system and int(user_id) not in database.blocked_users
    ] if not users_ids else users_ids:
        if system and database.user(str(user)).system != system:
            continue

        await asyncio.sleep(3)
        with contextlib.suppress(Exception):
            await notification_message.copy_to(user)
            successfully_sent += 1

        if delete_users:
            database.set(str(user), {})

    await _message.edit_text(
        text=Texts.Admin.NOTIFY_SUCCESS.format(
            successfully_sent=pluralization_string(
                successfully_sent,
                ["пользователю", "пользователям", "пользователям"]
            )
        )
    )


@router.message(Command("shutdown"), AdminFilter)
async def shutdown(message: Message):
    await message.react([ReactionTypeEmoji(emoji="👌")])
    os._exit(0) # noqa
