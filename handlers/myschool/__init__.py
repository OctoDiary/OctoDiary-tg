from . import _loop, homeworks, marks, profile, schedule, settings
from .router import router as MySchoolRouter

__all__ = [
    "MySchoolRouter",
    "_loop",
    "schedule",
    "settings",
    "homeworks",
    "marks",
    "profile",
]