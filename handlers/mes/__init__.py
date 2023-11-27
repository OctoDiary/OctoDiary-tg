#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers.mes import homeworks, inline_query, loop, marks, profile, schedule, scheduler, settings, visits
from handlers.mes.router import router as MesRouter

__all__ = [
    "MesRouter",
    "loop",
    "homeworks",
    "inline_query",
    "marks",
    "profile",
    "schedule",
    "scheduler",
    "settings",
    "visits"
]
