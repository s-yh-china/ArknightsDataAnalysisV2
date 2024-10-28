from fastapi import APIRouter

from src.api.email import EmailVerifyInfo, EmailVerifyToken
from src.api.email import email_verify

router = APIRouter(
    prefix="/api/email",
    tags=["email"]
)


@router.post('/verify', response_model=EmailVerifyInfo)
async def verify_email(token: EmailVerifyToken):
    return await email_verify(token.token)
