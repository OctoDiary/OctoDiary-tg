#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers import inline_query, profile, schedule, scheduler, settings, visits
from handlers.loop import LoopRouter
from handlers.router import router as UserRouter

routers = [
    LoopRouter,
    UserRouter,
]
