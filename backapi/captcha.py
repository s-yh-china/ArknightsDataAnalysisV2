from fastapi import APIRouter, Depends

from api.captcha import CaptchaInfo
from api.captcha import create_captcha_code, valid_captcha_code
from api.utils import JustMsgModel

router = APIRouter(
    prefix="/api/captcha",
    tags=["captcha"],
    responses={404: {"description": "Not found"}}
)


# TODO 速率控制
@router.get("/create", response_model=CaptchaInfo)
def get_captcha():  # 不是异步 因为图像库不是异步
    info: CaptchaInfo = create_captcha_code()
    return info


@router.post("/validate", response_model=JustMsgModel, dependencies=[Depends(valid_captcha_code)])
def validate_captcha():
    return JustMsgModel()
