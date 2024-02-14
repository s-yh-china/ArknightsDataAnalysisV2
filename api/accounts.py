import asyncio

from .models import Account, AccountChannel, DBUser, database_manager
from .users import UserBase, get_current_active_user
from .arknights_data_analysis import ArknightsDataAnalysis

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
        return await database_manager.get_or_none(Account, Account.uid == self.uid)


class AccountRefresh(AccountBase):
    fcore: bool
    token: str = None


class AccountCreate(BaseModel):
    token: str
    channel: AccountChannel


async def get_accounts(user: UserBase) -> list[AccountInDB]:
    accounts = []
    for account in await database_manager.execute(Account.select().join_from(Account, DBUser).where(DBUser.username == user.username)):
        await ArknightsDataAnalysis.get_analysis(account)  # TODO 太慢了 单独处理为一个api
        accounts.append(AccountInDB(**account.__data__))
    return accounts


async def get_account_by_token(account_create: AccountCreate) -> AccountInDB:
    analysis: ArknightsDataAnalysis
    created: bool
    analysis, created = await ArknightsDataAnalysis.get_or_create_analysis(account_create.token, account_create.channel)
    if analysis:
        return AccountInDB(**analysis.account.__data__)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Invalid"
        )


async def add_account_to_user(account_create: AccountCreate, user: UserBase):
    account: Account = await database_manager.get_or_none(Account, token=account_create.token)
    dbuser: DBUser = await database_manager.get_or_none(DBUser, username=user.username)
    if account and dbuser:
        account.owner = dbuser
        await database_manager.update(account)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Accepted"
        )


async def get_account_by_uid(account: AccountBase, user: UserBase = Depends(get_current_active_user)) -> AccountInDB:
    db_account: Account = await database_manager.get_or_none(Account, uid=account.uid)
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account Not Found"
        )

    if user.username != db_account.owner.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Accepted"
        )

    return AccountInDB(**db_account.__data__)


async def del_account_by_uid(account: AccountInDB):  # TODO 还没做
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

    task = asyncio.create_task(analysis.fetch_data(refresh_info.fcore))
