#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from core.handlers.diary import router as diary_router
from core.handlers.other import router as other_router
from core.handlers.start import router as start_router
from core.handlers.settings import router as settings_router
from core.handlers.inline import router as inline_router
from core.handlers.feedback import router as feedback_router
from core.handlers.auth import router as auth_router
from core.handlers.admins import router as admins_router
from core.misc.loops import router as loops_router

from core.handlers import exceptions

routers = [
    start_router,
    admins_router,
    auth_router,
    diary_router,
    feedback_router,
    loops_router,
    inline_router,
    other_router,
    settings_router,
]
