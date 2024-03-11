from fastapi import APIRouter

from api.email import EmailVerifyInfo, EmailVerifyToken
from api.email import email_verify

router = APIRouter(
    prefix="/api/email",
    tags=["email"],
    responses={404: {"description": "Not found"}}
)


@router.post('/verify', response_model=EmailVerifyInfo)
async def verify_email(token: EmailVerifyToken):
    return await email_verify(token.token)
