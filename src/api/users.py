from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from jose import JWTError
from pydantic import BaseModel
from bcrypt import checkpw, hashpw, gensalt

from src.api.databases import DBUser
from src.api.models import UserConfig
from src.api.utils import decode_jwt


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


class UserInfo(UserBase):
    disabled: bool
    user_config: UserConfig


class UserInDB(UserInfo):
    hashed_password: str

    class Config:
        from_attributes = True

    async def get_db(self) -> DBUser | None:
        return await DBUser.aio_get_or_none(DBUser.username == self.username)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return checkpw(plain_password.encode(), hashed_password.encode())


async def get_user(username: str) -> UserInDB | None:
    if user := await DBUser.aio_get_or_none(DBUser.username == username):
        return UserInDB(**user.__data__)


async def get_user_email(email: str) -> UserInDB | None:
    if user := await DBUser.aio_get_or_none(DBUser.email == email):
        return UserInDB(**user.__data__)


async def authenticate_user(username: str, password: str) -> UserInfo | None:
    user: UserInDB | None = await get_user(username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="api/users/login_password")


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return current_user


def get_password_hash(password: str) -> str:
    return hashpw(password.encode(), gensalt()).decode()


async def create_user(username: str, password: str, email: str) -> UserInfo:
    password = get_password_hash(password)
    await DBUser.aio_create(username=username, hashed_password=password, email=email, user_config=UserConfig().model_dump_json())
    return await get_user(username)


async def modify_user_config(user: UserInDB, config: UserConfig) -> None:
    db_user = await user.get_db()
    db_user.user_config = config.model_dump_json()
    await db_user.aio_save()
