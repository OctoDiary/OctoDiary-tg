from .router import router as MySchoolRouter
from . import _loop, schedule, settings, homeworks, marks, profile


__all__ = [
    "MySchoolRouter",
    "_loop",
    "schedule",
    "settings",
    "homeworks",
    "marks",
    "profile",
]