import aiosmtplib

from fastapi import HTTPException, status
from jose import JWTError
from datetime import timedelta
from email.message import EmailMessage

from pydantic import BaseModel

from src.config import conf
from src.api.databases import DBUser
from src.api.users import get_user_by_email, UserInDB, get_password_hash
from src.api.utils import decode_jwt, create_jwt, JustMsgModel
from src.api.datas import EmailInfo
from src.data_store import get_res_path


class EmailResetPassword(BaseModel):
    email: str
    new_password: str


class EmailVerifyToken(BaseModel):
    token: str


class EmailVerifyInfo(JustMsgModel):
    type: str


async def send_email(to_address: str, token: str, type: str):
    email_data = EmailInfo.get_email(type)

    message = EmailMessage()

    message["From"] = email_data['from'].replace('%EMAIL%', conf.email.username)
    message["To"] = to_address
    message["Subject"] = email_data['subject']
    with open(get_res_path() / email_data['content_file'], encoding='utf-8') as email_file:
        email_context = email_file.read()
        email_context = email_context.replace('%TOKEN%', token)
        message.add_alternative(email_context, subtype='html')

    await aiosmtplib.send(
        message,
        hostname=conf.email.smtp,
        port=conf.email.port,
        username=conf.email.username,
        password=conf.email.password,
        use_tls=conf.email.use_tls,
    )


async def email_verify(verify_token: str) -> EmailVerifyInfo:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_jwt(verify_token)
        email: str = payload.get("email")
        type: str = payload.get("type")

        if email is None or type is None:
            raise credentials_exception
        user: UserInDB = await get_user_by_email(email)
        if user is None:
            raise credentials_exception
        db_user = await user.get_db()

        match type:
            case "verify_email":
                db_user.disabled = False
                await db_user.aio_save()
            case "change_password":
                db_user.hashed_password = payload.get("new_hashed_password")
                await db_user.aio_save()
            case _:
                raise credentials_exception
    except JWTError:
        raise credentials_exception

    return EmailVerifyInfo(type=type)


async def create_email_verify(email: str, type: str, ex_data: dict = None) -> str:
    user: UserInDB = await get_user_by_email(email)
    db_user: DBUser = await user.get_db()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found",
        )

    if not ex_data:
        ex_data = {}

    data = {
        'email': email,
        'type': type
    }

    match type:
        case "verify_email":
            db_user.disabled = True
            await db_user.aio_save()
        case "change_password":
            new_hashed_password: str = get_password_hash(ex_data.get('new_password'))
            data.update({
                'new_hashed_password': new_hashed_password
            })
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid type"
            )

    return create_jwt(data, timedelta(hours=12))
