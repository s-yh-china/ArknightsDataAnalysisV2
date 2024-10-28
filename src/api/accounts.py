import asyncio

from src.api.databases import Account, AccountChannel, DBUser
from src.api.users import UserBase, UserInDB, get_current_active_user
from src.api.arknights_data_analysis import ArknightsDataAnalysis

from fastapi import HTTPException, status, Depends
from pydantic import BaseModel, ConfigDict


class AccountBase(BaseModel):
    uid: str


class AccountInfo(AccountBase):
    nickname: str
    channel: AccountChannel
    available: bool


class AccountInDB(AccountInfo):
    model_config = ConfigDict(from_attributes=True)

    id: int
    token: str

    async def get_db(self) -> Account:
        return await Account.aio_get(Account.id == self.id)


class AccountRefresh(AccountBase):
    force: bool = False
    token: str | None = None


class AccountCreate(BaseModel):
    token: str
    channel: AccountChannel


async def get_accounts(user: UserBase) -> list[AccountInDB]:
    accounts = []
    for account in await Account.select().join_from(Account, DBUser).where(DBUser.username == user.username).aio_execute():
        accounts.append(AccountInDB.model_validate(account))
    return accounts


async def get_account_by_token(account_create: AccountCreate) -> AccountInDB:
    analysis: ArknightsDataAnalysis
    created: bool
    analysis, created = await ArknightsDataAnalysis.get_or_create_analysis(account_create.token, account_create.channel)
    if analysis:
        if created:
            _ = asyncio.create_task(analysis.fetch_data(True))
        return AccountInDB.model_validate(analysis.account)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="account.create.token_invalid"
        )


async def add_account_to_user(account_create: AccountCreate, user: UserInDB):
    dbuser: DBUser = await user.get_db()
    account: Account = await Account.aio_get_or_none(Account.token == account_create.token)
    if account and dbuser:
        account.owner = dbuser
        await account.aio_save()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account.create.token_invalid"
        )


async def get_account_by_uid(account: AccountBase, user: UserBase = Depends(get_current_active_user)) -> AccountInDB:
    db_account: Account = await Account.aio_get_by_uid(account.uid)
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="account.not_found"
        )

    if user.id != db_account.owner.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account.not_owner"
        )

    return AccountInDB.model_validate(db_account)


async def del_account(account: AccountInDB):
    db_account: Account = await account.get_db()
    if db_account.owner:
        db_account.owner = None
        db_account.token = ''
        db_account.available = False
        await db_account.aio_save()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account.remove.no_owner"
        )


async def refresh_account_data(account: AccountInDB, refresh_info: AccountRefresh):
    db_account: Account = await account.get_db()

    analysis: ArknightsDataAnalysis
    if refresh_info.token:
        analysis = (await ArknightsDataAnalysis.get_or_create_analysis(refresh_info.token, db_account.channel))[0]
    else:
        analysis = await ArknightsDataAnalysis.get_analysis(db_account)

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account.refresh.token_invalid"
        )

    _ = asyncio.create_task(analysis.fetch_data(refresh_info.force))
