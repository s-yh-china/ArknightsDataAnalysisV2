from fastapi import APIRouter, Depends, status, UploadFile

from src.api.users import get_current_active_user, UserBase, UserInDB
from src.api.accounts import AccountInfo, AccountInDB, AccountCreate, AccountRefresh, AccountBase
from src.api.accounts import get_accounts, get_account_by_token, add_account_to_user, get_account_by_uid, del_account
from src.api.accounts import refresh_account_data
from src.api.arkgacha_data_import import data_import
from src.api.utils import JustMsgModel
from src.api.captcha import valid_captcha_code, CaptchaValid

router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"]
)


@router.get("/list", response_model=list[AccountInfo])
async def list_accounts(current_user: UserBase = Depends(get_current_active_user)):
    return await get_accounts(current_user)


@router.post("/create", response_model=AccountInfo, dependencies=[Depends(get_current_active_user)])
async def create_account(account: AccountInfo = Depends(get_account_by_token)):
    return account


@router.post("/add_to_user", response_model=JustMsgModel)
async def add_account(account: AccountCreate, current_user: UserInDB = Depends(get_current_active_user)):
    await add_account_to_user(account, current_user)
    return JustMsgModel()


@router.post("/info", response_model=AccountInfo)
async def account_info(account: AccountInfo = Depends(get_account_by_uid)):
    return account


@router.post("/delete", response_model=JustMsgModel, dependencies=[Depends(valid_captcha_code)])
async def delete_account(account: AccountInDB = Depends(get_account_by_uid)):
    await del_account(account)
    return JustMsgModel()


@router.post("/refresh", response_model=JustMsgModel, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(valid_captcha_code)])
async def refresh_account(account: AccountRefresh, current_user: UserBase = Depends(get_current_active_user)):
    account_info: AccountInDB = await get_account_by_uid(account, current_user)
    await refresh_account_data(account_info, account)
    return JustMsgModel(code=202, msg="accept")


@router.post("/import_from_arkgacha", status_code=status.HTTP_202_ACCEPTED, response_model=JustMsgModel)
async def import_from_arkgacha(file: UploadFile, uid: str, captcha_token: str, code: str, user: UserBase = Depends(get_current_active_user)):
    valid_captcha_code(CaptchaValid(captcha_token=captcha_token, code=code))
    account = await get_account_by_uid(AccountBase(uid=uid), user)
    file = await file.read()
    await data_import(file, account)
    return JustMsgModel(code=202, msg="accept")
