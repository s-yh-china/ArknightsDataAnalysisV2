from fastapi import APIRouter, Depends, HTTPException, status

from api.pydantic_models import PoolProgress, PoolInfo
from api.accounts import get_current_active_user
from api.datas import AnalysisData
from api.models import database_manager, OSRPool

router = APIRouter(
    prefix="/api/utils",
    tags=["utils"],
    responses={404: {"description": "Not found"}}
)

pool_data = AnalysisData().get_data()['pool_progress']


@router.get('/pool_progress', dependencies=[Depends(get_current_active_user)], response_model=PoolProgress)
def pool_progress():
    return PoolProgress(**pool_data)


@router.get('/pool_info', dependencies=[Depends(get_current_active_user)], response_model=PoolInfo)
async def pool_info(pool_name: str):
    pool: OSRPool = await database_manager.get_or_none(OSRPool, name=pool_name)
    if not pool:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pool not found")
    return PoolInfo(**pool.__data__)
