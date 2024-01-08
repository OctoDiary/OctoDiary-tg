#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from octodiary.asyncApi.mes import AsyncMobileAPI as MesAsyncMobileAPI
from octodiary.asyncApi.myschool import AsyncMobileAPI as MySchoolAsyncMobileAPI
from octodiary.asyncApi.myschool import AsyncWebAPI as MySchoolAsyncWebAPI


class MesAPIs:
    def __init__(self, token: str) -> None:
        self.mobile: MesAsyncMobileAPI = MesAsyncMobileAPI(token)
        self.web = None


class MySchoolAPIs:
    def __init__(self, token: str) -> None:
        self.mobile: MySchoolAsyncMobileAPI = MySchoolAsyncMobileAPI(token)
        self.web: MySchoolAsyncWebAPI = MySchoolAsyncWebAPI(token)
