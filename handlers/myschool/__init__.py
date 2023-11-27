#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers.myschool import loop, homeworks, inline_query, marks, profile, schedule, scheduler, settings
from handlers.myschool.router import router as MySchoolRouter

__all__ = [
    "MySchoolRouter",
    "loop.py",
    "homeworks",
    "inline_query",
    "marks",
    "profile",
    "schedule",
    "scheduler",
    "settings"
]
