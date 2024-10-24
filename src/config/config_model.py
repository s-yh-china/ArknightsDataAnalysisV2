from pydantic import BaseModel


class COSRConfig(BaseModel):
    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]


class SafeConfig(BaseModel):
    SECRET_KEY: str
    ALGORITHM: str  # TODO enum
    DEBUG: bool
    LOG_LEVEL: str  # TODO enum
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


# TODO corn check
class AnalysisConfig(BaseModel):
    update_time: str
    auto_gift: str
    pool_info_update: str
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
