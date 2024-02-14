from fastapi import APIRouter, Depends

from api.accounts import AccountInDB, get_account_by_uid
from api.account_datas import OSRInfo
from api.account_datas import get_osr_info

router = APIRouter(
    prefix="/api/accounts/data",
    tags=["account datas"],
    responses={404: {"description": "Not found"}}
)


@router.post("/osr_info", response_model=OSRInfo)
async def account_info(account: AccountInDB = Depends(get_account_by_uid)):
    return await get_osr_info(account)
