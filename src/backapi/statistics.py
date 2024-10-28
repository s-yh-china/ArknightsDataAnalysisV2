from fastapi import APIRouter, Depends

from src.api.statistics import LuckyRankInfo, PoolLuckyRankInfo, UPRankInfo, SiteStatisticsInfo
from src.api.statistics import get_lucky_rank_info, get_pool_lucky_rank_info, get_six_up_rank_info, get_site_statistics_info
from src.api.users import UserInDB, get_current_active_user
from src.api.utils import JustMsgModel

router = APIRouter(
    prefix="/api/statistics",
    tags=["statistics"]
)


@router.get("/lucky_rank", response_model=LuckyRankInfo | JustMsgModel)
async def lucky_rank(current_user: UserInDB = Depends(get_current_active_user)):
    info: LuckyRankInfo = await get_lucky_rank_info(current_user)
    if info is None:
        return JustMsgModel(code=404, msg="No lucky rank info available")
    return info


@router.get("/pool_lucky_rank", response_model=PoolLuckyRankInfo | JustMsgModel)
async def pool_lucky_rank(current_user: UserInDB = Depends(get_current_active_user)):
    info: LuckyRankInfo = await get_pool_lucky_rank_info(current_user)
    if info is None:
        return JustMsgModel(code=404, msg="No pool lucky rank info available")
    return info


@router.get("/six_up_rank", response_model=UPRankInfo | JustMsgModel)
async def six_up_rank(current_user: UserInDB = Depends(get_current_active_user)):
    info: UPRankInfo = await get_six_up_rank_info(current_user)
    if info is None:
        return JustMsgModel(code=404, msg="No six up rank info available")
    return info


@router.get("/site_statistics", response_model=SiteStatisticsInfo, dependencies=[Depends(get_current_active_user)])
async def site_statistics():
    return await get_site_statistics_info()
