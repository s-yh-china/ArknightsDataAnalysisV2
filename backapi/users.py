from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.captcha import valid_captcha_code
from api.users import Token, UserInfo, UserCreate
from api.users import authenticate_user, get_current_active_user, get_user, create_user

from api.utils import create_jwt

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}}
)

ACCESS_TOKEN_EXPIRE_MINUTES = 60


@router.post("/login_password")
async def login_password(data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user: UserInfo = await authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_jwt(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh_token")
def refresh_token(current_user: UserInfo = Depends(get_current_active_user)) -> Token:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_jwt(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=UserInfo, dependencies=[Depends(valid_captcha_code)])
async def register(data: UserCreate) -> UserInfo:
    user: UserInfo = await get_user(data.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User already",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await create_user(data.username, data.password, data.email)
    return user


@router.get("/info", response_model=UserInfo)
async def info(current_user: UserInfo = Depends(get_current_active_user)) -> UserInfo:
    return current_user
