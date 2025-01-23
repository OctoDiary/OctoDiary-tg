#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from octodiary.apis import AsyncMobileAPI, AsyncWebAPI


class APIs:
    def __init__(self, token: str, system: str) -> None:
        self.mobile: AsyncMobileAPI = AsyncMobileAPI(token=token, system=system)
        self.web: AsyncWebAPI = AsyncWebAPI(token=token, system=system)
