from secrets import token_urlsafe
from typing import cast

import aiohttp

from datetime import timedelta, timezone, datetime
from pydantic import BaseModel
from jose import jwt

from src.api.datas import ConfigData


class JustMsgModel(BaseModel):
    code: int = 200
    msg: str = 'ok'


class AsyncRequest:
    def __init__(self):
        self._session: aiohttp.ClientSession

    async def __aenter__(self) -> 'AsyncRequest':
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._session.close()

    async def get(self, url: str) -> dict[str, object]:
        async with self._session.get(url) as response:
            if response.status / 100 == 2:
                return cast(dict[str, object], await response.json())
            else:
                raise ValueError(f'Response {url} status code is {response.status}')

    async def post_json(self, url: str, json_data: dict[str, object]) -> dict[str, object]:
        async with self._session.post(url, json=json_data) as response:
            if response.status / 100 == 2:
                return cast(dict[str, object], await response.json())
            else:
                raise ValueError(f'Response {url} status code is {response.status}')

    async def post_json_with_csrf(self, url: str, json_data: dict[str, object]) -> dict[str, object]:
        token = token_urlsafe(24)
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58',
            'x-csrf-token': token,
            'cookie': f'csrf_token={token}',
            'content-type': 'application/json;charset=UTF-8'
        }
        async with self._session.post(url, json=json_data, headers=headers) as response:
            if response.status / 100 == 2:
                return cast(dict[str, object], await response.json())
            else:
                raise ValueError(f'Response {url} status code is {response.status}')

    @staticmethod
    def get_response[T](__type: type[T], response: dict[str, object]) -> T:
        return cast(__type, response.get('data'))


def f_hide_mid(info: str, count: int = 4, fix: str = '*') -> str:
    """
    隐藏/脱敏中间几位
    :param info: 输入字符串
    :param count: 隐藏位数
    :param fix: 替换符号
    :return: 脱敏后的字符串
    """
    if not info:
        return ''

    str_len: int = len(info)

    if str_len <= 2:
        return info

    if count >= str_len - 2:
        return info[0] + fix * (str_len - 2) + info[-1]

    mid_pos: int = str_len // 2
    offset: int = count // 2

    ret_str: str
    if count % 2 == 0:
        ret_str = info[:mid_pos - offset] + count * fix + info[mid_pos + offset:]
    else:
        ret_str = info[:mid_pos - offset] + count * fix + info[mid_pos + offset + 1:]

    return ret_str


def create_jwt(data: dict, expires_delta: timedelta = timedelta(minutes=60)) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, ConfigData.get_safe()['SECRET_KEY'], algorithm=ConfigData.get_safe()['ALGORITHM'])
    return encoded_jwt


def decode_jwt(encoded_jwt: str) -> dict:
    return jwt.decode(encoded_jwt, ConfigData.get_safe()['SECRET_KEY'], algorithms=ConfigData.get_safe()['ALGORITHM'])
