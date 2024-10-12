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
    pools: list[str]


class PoolInfoModel(BaseModel):
    id: str
    name: str
    real_name: str
    type: str
    start: int
    end: int
    up_char_info: list[str] | None = None
    limited_char_info: list[str] | None = None
    weight_up_char_info: dict[str, int] | None = None
