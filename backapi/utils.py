from fastapi import APIRouter, Depends

from api.pydantic_models import PoolProgress, PoolInfoModel
from api.accounts import get_current_active_user
from api.datas import PoolInfo

router = APIRouter(
    prefix="/api/utils",
    tags=["utils"],
    responses={404: {"description": "Not found"}}
)


@router.get('/pool_progress', dependencies=[Depends(get_current_active_user)], response_model=PoolProgress)
def pool_progress():
    return PoolProgress.model_validate({'pools': PoolInfo.get_now_pools()})


@router.get('/pool_info', dependencies=[Depends(get_current_active_user)], response_model=PoolInfoModel)
async def pool_info(pool_id: str):
    return PoolInfoModel.model_validate(PoolInfo.get_pool_info(pool_id))
