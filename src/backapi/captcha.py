from fastapi import APIRouter, Depends

from src.api.captcha import CaptchaInfo
from src.api.captcha import create_captcha_code, valid_captcha_code
from src.api.utils import JustMsgModel

router = APIRouter(
    prefix="/api/captcha",
    tags=["captcha"]
)


# TODO 速率控制
@router.get("/create", response_model=CaptchaInfo)
def get_captcha():  # 不是异步 因为图像库不是异步
    return create_captcha_code()


@router.post("/validate", response_model=JustMsgModel, dependencies=[Depends(valid_captcha_code)])
def validate_captcha():
    return JustMsgModel()
