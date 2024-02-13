import secrets
import aiohttp

from datetime import timedelta, timezone, datetime
from pydantic import BaseModel
from jose import jwt

from .datas import ConfigData

config = ConfigData().get_data()['safe']

SECRET_KEY = config['SECRET_KEY']
ALGORITHM = config['ALGORITHM']


class JustMsgModel(BaseModel):
    code: int = 200
    msg: str = 'ok'


class AsyncRequest:
    async def __aenter__(self) -> 'AsyncRequest':
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.session.close()

    async def get(self, url: str, json_response: bool = True) -> bytes | str:
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.read() if not json_response else await response.json()
        return 'ERROR'

    async def post_json(self, url: str, json: dict, json_response: bool = True) -> bytes | str:
        async with self.session.post(url, json=json) as response:
            if response.status == 200:
                return await response.read() if not json_response else await response.json()
        return 'ERROR'

    async def post_json_with_csrf(self, url: str, json: dict, json_response: bool = True) -> bytes | str:
        token = secrets.token_urlsafe(24)
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58',
            'x-csrf-token': token,
            'cookie': f'csrf_token={token}',
            'content-type': 'application/json;charset=UTF-8'
        }
        async with self.session.post(url, json=json, headers=headers) as response:
            if response.status == 200:
                return await response.read() if not json_response else await response.json()
        return 'ERROR'


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

    if count % 2 == 0:
        ret_str: str = info[:mid_pos - offset] + count * fix + info[mid_pos + offset:]
    else:
        ret_str: str = info[:mid_pos - offset] + count * fix + info[mid_pos + offset + 1:]

    return ret_str


def create_jwt(data: dict, expires_delta: timedelta = timedelta(minutes=60)) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt(encoded_jwt: str) -> dict:
    return jwt.decode(encoded_jwt, SECRET_KEY, algorithms=[ALGORITHM])
