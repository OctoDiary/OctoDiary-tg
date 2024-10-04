#               © Copyright 2023
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from handlers.admins import commands, statistics
from handlers.admins.router import AdminRouter

__all__ = [
    "AdminRouter",
    "commands"
]
