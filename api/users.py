import os
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from jose import JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from .models import DBUser
from .models import database_manager
from .utils import decode_jwt


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


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


class UserInfo(UserBase):
    disabled: bool
    user_config: UserConfig


class UserInDB(UserInfo):
    hashed_password: str
    slat: str

    class Config:
        from_attributes = True

    async def get_db(self) -> DBUser | None:
        return await database_manager.get_or_none(DBUser, DBUser.username == self.username)


password_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="api/users/login_password")


def verify_password(plain_password: str, slat: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password + slat, hashed_password)


async def get_user(username: str) -> UserInDB | None:
    user: DBUser = await database_manager.get_or_none(DBUser, username=username)
    if user:
        user_config: UserConfig = UserConfig.model_validate_json(user.user_config)
        return UserInDB.model_validate({**user.__data__, "user_config": user_config})


async def get_user_email(email: str) -> UserInDB | None:
    user: DBUser = await database_manager.get_or_none(DBUser, email=email)
    if user:
        user_config: UserConfig = UserConfig.model_validate_json(user.user_config)
        return UserInDB.model_validate({**user.__data__, "user_config": user_config})


async def authenticate_user(username: str, password: str) -> UserInfo | bool:
    user: UserInDB | None = await get_user(username)
    if not user:
        return False
    if not verify_password(password, user.slat, user.hashed_password):
        return False
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_jwt(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = await get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: UserInfo = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_password_hash(password: str, slat: str) -> str:
    return password_context.hash(password + slat)


async def create_user(username: str, password: str, email: str) -> UserInfo:
    slat: str = os.urandom(16).hex()
    password = get_password_hash(password, slat)
    await database_manager.create(DBUser, username=username, hashed_password=password, email=email, slat=slat, user_config=UserConfig().model_dump_json())
    return await get_user(username)


async def modify_user_config(user: UserInDB, config: UserConfig):
    db_user = await user.get_db()
    db_user.user_config = config.model_dump_json()
    await database_manager.update(db_user)
