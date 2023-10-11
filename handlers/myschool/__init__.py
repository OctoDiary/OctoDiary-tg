#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers.myschool import _loop, homeworks, inline_query, marks, profile, schedule, scheduler, settings
from handlers.myschool.router import router as MySchoolRouter

__all__ = [
    "MySchoolRouter",
    "_loop",
    "schedule",
    "settings",
    "homeworks",
    "marks",
    "profile",
]
