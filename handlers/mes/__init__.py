#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers.mes.router import router as MesRouter
from . import _loop, homeworks, inline_query, marks, profile, schedule, scheduler, settings, visits

__all__ = [
    "MesRouter",
    "_loop",
    "homeworks",
    "inline_query",
    "marks",
    "profile",
    "schedule",
    "scheduler",
    "settings",
    "visits"
]
