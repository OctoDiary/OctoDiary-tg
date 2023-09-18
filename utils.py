#    ____       _        _____  _                  
#   / __ \     | |      |  __ \(_)                 
#  | |  | | ___| |_ ___ | |  | |_  __ _ _ __ _   _ 
#  | |  | |/ __| __/ _ \| |  | | |/ _` | '__| | | |
#  | |__| | (__| || (_) | |__| | | (_| | |  | |_| |
#   \____/ \___|\__\___/|_____/|_|\__,_|_|   \__, |
#                                             __/ |
#                                            |___/ 
# 
#                 © Copyright 2023
#        🔒 Licensed under the MIT License
#        https://opensource.org/licenses/MIT


import os
import signal
import sys


def restart():
    signal.signal(
        signal.SIGTERM,
        (
            lambda *_: os.execl(
                sys.executable,
                sys.executable,
                "main.py",
                *sys.argv[1:],
            )
        )
    )
    os.killpg(os.getpgid(os.getpid()), signal.SIGTERM)

