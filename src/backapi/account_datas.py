from fastapi import APIRouter, Depends

from src.api.accounts import AccountInDB, get_account_by_uid
from src.api.account_datas import OSRInfo, OSRPoolInfo, PayRecordInfo, DiamondInfo
from src.api.account_datas import get_osr_info, get_osr_pool_info, get_pay_record_info, get_diamond_info

router = APIRouter(
    prefix="/api/accounts/data",
    tags=["account datas"]
)


@router.post("/osr_info", response_model=OSRInfo)
async def account_info(account: AccountInDB = Depends(get_account_by_uid)):
    return await get_osr_info(account)


@router.post("/osr_pool_info", response_model=OSRPoolInfo)
async def account_pool_info(pool: str, account: AccountInDB = Depends(get_account_by_uid)):
    return await get_osr_pool_info(account, pool)


@router.post("/pay_record_info", response_model=PayRecordInfo)
async def account_pay_record_info(account: AccountInDB = Depends(get_account_by_uid)):
    return await get_pay_record_info(account)


@router.post("/diamond_info", response_model=DiamondInfo)
async def account_diamond_info(account: AccountInDB = Depends(get_account_by_uid)):
    return await get_diamond_info(account)
