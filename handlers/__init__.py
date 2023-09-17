from .mesh import MeshRouter
from .start import router as StartRouter, auth_router as AuthRouter
from .myschool import MySchoolRouter

routers = [
    StartRouter,
    AuthRouter,
    MySchoolRouter,
    MeshRouter,
]