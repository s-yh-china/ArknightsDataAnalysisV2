import os
import re
import sys
import logging
import inspect

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, override, Any
from pathlib import Path

import loguru

from src.api.datas import ConfigData
from src.data_store import get_res_path

if TYPE_CHECKING:
    # avoid     sphinx autodoc resolve annotation failed
    # because loguru module do not have `Logger` class actually
    from loguru import Logger  # pragma: no cover

LEVELSTRMAP = {
    "DEBUG": "DBG",
    "TRACE": "TRC",
    "INFO": "INF",
    "WARNING": "WRN",
    "ERROR": "ERR",
    "CRITICAL": "CRT",
}
HTTP_STATUS_TEXT_MAP = {
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    103: "Early Hints",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi Status",
    208: "Already Reported",
    226: "I'm Used",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    306: "Reserved",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "GONE",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request URI Too Long",
    415: "Unsupported Media Type",
    416: "Requested Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm A Teapot",
    421: "Misdirected Request",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    425: "Too Early",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    451: "Unavailable For Legal Reasons",
    480: "Temporarily Unavailable",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "Http Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    510: "Not Extended",
    511: "Network Authentication Required",
}
INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")

logger: "Logger" = loguru.logger


# https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
class InterceptHandler(logging.Handler):
    @override
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


class ColorizedHTTPStatus:
    @classmethod
    def colorize(cls, status_code: int) -> str:
        status_text = HTTP_STATUS_TEXT_MAP.get(status_code, "")
        if 200 <= status_code < 300:
            return f" \033[0;32m{status_code} {status_text}\033[0m"
        if 300 <= status_code < 400:
            return f" \033[0;33m{status_code} {status_text}\033[0m"
        if 400 <= status_code < 500:
            return f" \033[0;31m{status_code} {status_text}\033[0m"
        if 500 <= status_code < 600:
            return f" \033[0;35m{status_code} {status_text}\033[0m"
        return str(status_code)


def format_record(record: Any) -> str:
    time = "[<g>{time:YYYY-MM-DD HH:mm:ss.ss}</g>]"
    record["level"].name = LEVELSTRMAP.get(record["level"].name, record["level"].name)
    level = "[<lvl>{level}</lvl>]"
    def_name = "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
    message = "<level>{message}</level>"
    format_string = time + level + " - " + def_name + " | " + message
    if INTEGER_PATTERN.match(code := record["message"].split(" ")[-1]):
        record["message"] = record["message"].replace(f" {code}", ColorizedHTTPStatus.colorize(int(code)))
    format_string += "{exception}\n"

    return format_string


def get_log_file_path() -> Path:
    time_now = datetime.now()
    last_log = max(Path("./log").glob("log_*"), default=None, key=os.path.getmtime)

    if last_log and (time_now - datetime.fromtimestamp(last_log.stat().st_mtime)) < timedelta(hours=1):
        log_file = f"log/{last_log.name}"
    else:
        log_file = f'log/log_{time_now.strftime("%Y-%m-%d_%H-%M-%S")}.log'

    return Path(log_file)


safe_data = ConfigData.get_safe()
LEVEL: str = 'DEBUG' if safe_data['DEBUG'] else safe_data['LOG_LEVEL']

logger.remove()
logger.add(sys.stdout, level=LEVEL, diagnose=False, format=format_record)
logger.add(sink=get_res_path() / get_log_file_path(), format=format_record, level=LEVEL, diagnose=False)
