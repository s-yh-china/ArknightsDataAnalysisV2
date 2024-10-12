import asyncio

from src.api.databases import Account, AccountChannel, DBUser, database
from src.api.users import UserBase, UserInDB, get_current_active_user
from src.api.arknights_data_analysis import ArknightsDataAnalysis

from fastapi import HTTPException, status, Depends
from pydantic import BaseModel


class AccountBase(BaseModel):
    uid: str


class AccountInfo(AccountBase):
    nickname: str
    channel: AccountChannel
    available: bool


class AccountInDB(AccountInfo):
    token: str

    class Config:
        from_attributes = True

    async def get_db(self) -> Account | None:
        return await Account.aio_get_or_none(Account.uid == self.uid)


class AccountRefresh(AccountBase):
    force: bool
    token: str = None


class AccountCreate(BaseModel):
    token: str
    channel: AccountChannel


async def get_accounts(user: UserBase) -> list[AccountInDB]:
    accounts = []
    for account in await Account.select().join_from(Account, DBUser).where(DBUser.username == user.username).aio_execute():
        await ArknightsDataAnalysis.get_analysis(account)
        accounts.append(AccountInDB(**account.__data__))
    return accounts


async def get_account_by_token(account_create: AccountCreate) -> AccountInDB:
    analysis: ArknightsDataAnalysis
    created: bool
    analysis, created = await ArknightsDataAnalysis.get_or_create_analysis(account_create.token, account_create.channel)
    if analysis:
        if created:
            _ = asyncio.create_task(analysis.fetch_data(True))
        return AccountInDB(**analysis.account.__data__)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Invalid"
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
            detail="Not Accepted"
        )


async def get_account_by_uid(account: AccountBase, user: UserBase = Depends(get_current_active_user)) -> AccountInDB:
    db_account: Account = await Account.aio_get_or_none(Account.uid == account.uid)
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account Not Found"
        )

    with database.allow_sync():
        if user.username != db_account.owner.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not Accepted"
            )

    return AccountInDB(**db_account.__data__)


async def del_account_by_uid(account: AccountInDB):
    db_account: Account = await account.get_db()
    if db_account.owner:
        db_account.owner = None
        db_account.token = ''
        db_account.available = False
        await db_account.aio_save()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Accepted"
        )


async def refresh_account_data(account: AccountInDB, refresh_info: AccountRefresh):
    db_account: Account = await account.get_db()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account Not Found"
        )

    analysis: ArknightsDataAnalysis
    if refresh_info.token:
        analysis = (await ArknightsDataAnalysis.get_or_create_analysis(refresh_info.token, db_account.channel))[0]
    else:
        analysis = await ArknightsDataAnalysis.get_analysis(db_account)

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account Token Invalid, Need Refresh Token"
        )

    _ = asyncio.create_task(analysis.fetch_data(refresh_info.force))
