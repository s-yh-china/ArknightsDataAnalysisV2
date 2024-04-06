# 这是一个特殊的文件 为了避免循环引用模型
# 以及一些独立的模型
from enum import Enum

from pydantic import BaseModel


class UsernameDisplayStatus(Enum):
    FULL = 'FULL'
    HIDE_MID = 'HIDE_MID'
    HIDE_ALL = 'HIDE_ALL'


class UserConfig(BaseModel):
    nickname: str = '未设置'
    private_qq: int = 0

    is_statistics: bool = True
    is_lucky_rank: bool = False
    is_auto_gift: bool = False

    name_display: UsernameDisplayStatus = UsernameDisplayStatus.HIDE_ALL
    nickname_display: bool = False


class PoolProgress(BaseModel):
    pool: str
    end_time: str


class PoolInfo(BaseModel):
    name: str
    type: str
    is_auto: bool
    is_up_pool: bool | None
    up_operators: list[str] | None

    class Config:
        from_attributes = True
