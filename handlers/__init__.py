#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers.admins import AdminRouter
from handlers.auth import auth_router as AuthRouter
from handlers.mesh import MeshRouter
from handlers.myschool import MySchoolRouter
from handlers.start import router as StartRouter

routers = [
    AdminRouter,
    AuthRouter,
    StartRouter,
    MySchoolRouter,
    MeshRouter,
]
