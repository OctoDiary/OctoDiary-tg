#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers import homeworks, inline_query, marks, profile, schedule, scheduler, settings, visits, web_auth
from handlers.admins import AdminRouter
from handlers.auth import auth_router as AuthRouter
from handlers.feedback import feedback as FeedbackRouter
from handlers.loop import LoopRouter
from handlers.router import router as UserRouter
from handlers.start import router as StartRouter

routers = [
    AdminRouter,
    AuthRouter,
    StartRouter,
    LoopRouter,
    FeedbackRouter,
    UserRouter,
]
