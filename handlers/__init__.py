#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from .admins import AdminRouter
from .mesh import MeshRouter
from .myschool import MySchoolRouter
from .start import auth_router as AuthRouter
from .start import router as StartRouter

routers = [
    AdminRouter,
    StartRouter,
    AuthRouter,
    MySchoolRouter,
    MeshRouter,
]