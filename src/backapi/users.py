from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm

from src.api.datas import ConfigData
from src.api.email import EmailResetPassword, create_email_verify, send_email
from src.api.users import Token, UserInfo, UserCreate, UserInDB, UserConfig
from src.api.users import authenticate_user, get_current_active_user, get_user, create_user, get_user_email
from src.api.users import modify_user_config

from src.api.captcha import valid_captcha_code
from src.api.utils import create_jwt, JustMsgModel

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
async def register(data: UserCreate, tasks: BackgroundTasks) -> UserInfo:
    user: UserInfo = await get_user(data.username)
    if not user:
        user = await get_user_email(data.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User already",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await create_user(data.username, data.password, data.email)

    if ConfigData.get_user()['verify_email']:
        token = await create_email_verify(data.email, 'verify_email')
        tasks.add_task(send_email, data.email, token, 'verify_email')

    return user


@router.get("/info", response_model=UserInfo)
async def info(current_user: UserInfo = Depends(get_current_active_user)) -> UserInfo:
    return current_user


@router.post("/modify_config", response_model=JustMsgModel)
async def modify_config(config: UserConfig, current_user: UserInDB = Depends(get_current_active_user)) -> JustMsgModel:
    await modify_user_config(current_user, config)
    return JustMsgModel()


@router.post('/password_reset', response_model=JustMsgModel, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(valid_captcha_code)])
async def password_reset(payload: EmailResetPassword, tasks: BackgroundTasks):
    if not ConfigData.get_user()['password_reset']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password reset is not allowed",
        )
    token = await create_email_verify(payload.email, 'change_password', payload.model_dump())
    tasks.add_task(send_email, payload.email, token, 'change_password')
    return JustMsgModel(code=202, msg="accept")
