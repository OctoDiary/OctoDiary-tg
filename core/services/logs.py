#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6 # noqa
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def init_loguru():
    logging.basicConfig(handlers=[InterceptHandler()], level=20, force=True)
    logger.level("MINIDEBUG", no=15, color="<blue>")
    logger.add(
        "logs/minidebug.log",
        level="MINIDEBUG",
        format="{time:MMMM D, YYYY >> HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
        rotation="3 MB",
        compression="zip",
        backtrace=True,
        diagnose=True,
        filter=(lambda record: record["level"].name == "MINIDEBUG"),
    )
    logger.add(
        "logs/error.log",
        level="ERROR",
        format="{time:MMMM D, YYYY >> HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
        rotation="3 MB",
        compression="zip",
        backtrace=True,
        diagnose=True,
        filter=(lambda record: record["level"].name == "ERROR"),
    )
    logger.add(
        "logs/info.log",
        level="INFO",
        format="{time:MMMM D, YYYY >> HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
        rotation="30 KB",
        compression="zip",
        diagnose=True,
        filter=(lambda record: record["level"].name in ["INFO", "WARNING"]),
    )
    logger.add(
        "logs/user_errors.log",
        level="ERROR",
        backtrace=True,
        diagnose=True,
        filter=(lambda record: record["level"].name == "ERROR" and "uid" in record["extra"]),
        format="{time:MMMM D, YYYY >> HH:mm:ss} | {level} | {module}:{function}:{line} | {extra[user_id]} {extra[username]} {extra[system]} | {message}",
    )
