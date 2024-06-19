import aiosmtplib

from fastapi import HTTPException, status
from jose import JWTError
from datetime import timedelta
from email.message import EmailMessage

from pydantic import BaseModel

from api.models import DBUser, database_manager
from api.users import get_user_email, UserInDB, get_password_hash, get_random_slat
from api.utils import decode_jwt, create_jwt, JustMsgModel
from api.datas import ConfigData


class EmailResetPassword(BaseModel):
    email: str
    new_password: str


class EmailVerifyToken(BaseModel):
    token: str


class EmailVerifyInfo(JustMsgModel):
    type: str


def build_email_verify_link(token: str) -> str:
    return f"{ConfigData.get_email()['link']}?token={token}"


async def send_email(to_address: str, token: str):
    message = EmailMessage()
    message["From"] = ConfigData.get_email()['username']
    message["To"] = to_address
    message["Subject"] = "密码重置 / 邮箱验证"

    html_content = f"""
    <html>
    <body>
    <h1>密码重置 / 邮箱验证</h1>
    <p>您好，</p>
    <p>我们收到了一个请求，要求重置您的密码 / 验证您的邮箱。点击下面的链接进行操作：</p>
    <a href="{build_email_verify_link(token)}">重置密码 / 验证邮箱</a>
    <p>如果您没有提出这个请求，您可以忽略这封邮件。</p>
    </body>
    </html>
    """
    message.add_alternative(html_content, subtype='html')

    await aiosmtplib.send(
        message,
        hostname=ConfigData.get_email()['smtp'],
        port=ConfigData.get_email()['port'],
        username=ConfigData.get_email()['username'],
        password=ConfigData.get_email()['password'],
        use_tls=ConfigData.get_email()['use_tls'],
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
        user: UserInDB = await get_user_email(email)
        if user is None:
            raise credentials_exception
        db_user = await user.get_db()

        match type:
            case "verify_email":
                db_user.disabled = False
                await database_manager.update(db_user)
            case "change_password":
                db_user.hashed_password = payload.get("new_hashed_password")
                db_user.slat = payload.get("new_slat")
                await database_manager.update(db_user)
            case _:
                raise credentials_exception
    except JWTError:
        raise credentials_exception

    return EmailVerifyInfo(type=type)


async def create_email_verify(email: str, type: str, ex_data: dict = None) -> str:
    user: UserInDB = await get_user_email(email)
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
            await database_manager.update(db_user)
        case "change_password":
            new_slat: str = get_random_slat()
            new_hashed_password: str = get_password_hash(ex_data.get('new_password'), new_slat)
            data.update({
                'new_hashed_password': new_hashed_password,
                'new_slat': new_slat
            })
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid type"
            )

    return create_jwt(data, timedelta(hours=12))
