import re

from pydantic import BaseModel
from pydantic.functional_validators import AfterValidator

from typing import Annotated


def check_cron(v: str):
    if not re.match(r'^(\*|([0-5]?\d)) (\*|([0-2]?\d)) (\*|([0-3]?\d)) (\*|([0-1]?\d)) (\*|([0-7]))$', v.strip()):
        raise ValueError(f'Invalid cron expression: {v}')
    return v


def check_log_level(v: str):
    if v not in ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']:
        raise ValueError(f'Invalid log level: {v}')
    return v


CronType = Annotated[str, AfterValidator(check_cron)]
LogLevelType = Annotated[str, AfterValidator(check_log_level)]


class COSRConfig(BaseModel):
    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]
    allow_origin_regex: list[str] | None


class SafeConfig(BaseModel):
    SECRET_KEY: str
    ALGORITHM: str  # TODO check
    DEBUG: bool
    LOG_LEVEL: LogLevelType
    CORS: COSRConfig


class UserConfig(BaseModel):
    email_verify: bool
    password_reset: bool


class EmailConfig(BaseModel):
    smtp: str
    port: int
    username: str
    password: str
    use_tls: bool


class AnalysisConfig(BaseModel):
    update_time: CronType
    auto_gift: CronType
    pool_info_update: CronType
    pool_info_url: str


class MysqlConfig(BaseModel):
    host: str
    user: str
    password: str
    database: str
    port: int


class WebConfig(BaseModel):
    host: str
    port: int
    workers: int | None
    forward_ip: list[str]


class ServerConfig(BaseModel):
    safe: SafeConfig
    user: UserConfig
    email: EmailConfig
    analysis: AnalysisConfig
    mysql: MysqlConfig
    web: WebConfig
