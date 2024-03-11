from fastapi import APIRouter, Depends, status

from api.statistics import LuckyRankInfo
from api.statistics import get_lucky_rank_info
from api.users import UserInDB, get_current_active_user
from api.utils import JustMsgModel

router = APIRouter(
    prefix="/api/statistics",
    tags=["statistics"],
    responses={404: {"description": "Not found"}}
)


@router.get("/lucky_rank", response_model=LuckyRankInfo | JustMsgModel)
async def lucky_rank(current_user: UserInDB = Depends(get_current_active_user)):
    info: LuckyRankInfo = await get_lucky_rank_info(current_user)
    if info is None:
        return JustMsgModel(code=404, msg="No lucky rank info available")
    return info