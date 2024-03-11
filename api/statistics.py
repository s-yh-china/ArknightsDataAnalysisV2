from datetime import datetime
from pydantic import BaseModel
from collections import defaultdict

from .cache import cached_with_refresh
from .users import UserInDB, UserConfig, UsernameDisplayStatus
from .models import Account, DBUser, database_manager, OperatorSearchRecord, OSROperator
from .utils import f_hide_mid


class LuckyRankUser(BaseModel):
    name: str
    six: int
    count: int
    avg: float


class LuckyRankInfo(BaseModel):
    lucky: list[LuckyRankUser]
    unlucky: list[LuckyRankUser]
    time: datetime


def get_confined_account_name(user: UserInDB, account: Account) -> str:
    if user.username == account.owner.name:
        return f'{account.nickname} (Owner)'

    username: str
    user_config: UserConfig = UserConfig.model_validate_json(account.owner.user_config)
    match user_config.name_display:
        case UsernameDisplayStatus.FULL:
            username = account.nickname
        case UsernameDisplayStatus.HIDE_MID:
            username = f_hide_mid(account.nickname, count=7)
        case UsernameDisplayStatus.HIDE_ALL:
            username = f'已匿名{account.uid[:2]}{account.uid[-2:]}'
        case _:
            username = 'ERROR'

    if user_config.nickname_display:
        username += f' ({user_config.nickname})'

    return username


async def get_lucky_rank_info(user: UserInDB) -> LuckyRankInfo | None:
    info: dict = await compute_lucky_rank()
    if info is None:
        return None

    for item in info['lucky']:
        item['name'] = get_confined_account_name(user, item['account'])
    for item in info['unlucky']:
        item['name'] = get_confined_account_name(user, item['account'])
    return LuckyRankInfo(**info)


@cached_with_refresh(ttl=3600, key_builder=lambda: 'lucky_rank_info')
async def compute_lucky_rank():
    enable_users: list[DBUser] = []

    user: DBUser
    for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)):
        user_config: UserConfig = UserConfig.model_validate_json(user.user_config)
        if user_config.is_lucky_rank:
            enable_users.append(user)

    osr_lucky = defaultdict(lambda: {'six': 0, 'count': 0, 'account': None, 'avg': 0.0})

    records = await database_manager.execute(OperatorSearchRecord.select().join_from(OperatorSearchRecord, Account).where(Account.owner.in_(enable_users)))

    for record in records:
        account = record.account
        osr_lucky[account.id]['account'] = account

        operator: OSROperator
        for operator in record.operators:
            osr_lucky[account.id]['count'] += 1
            if operator.rarity == 6:
                osr_lucky[account.id]['six'] += 1

    osr_lucky = [v for v in osr_lucky.values() if v['six'] > 5]
    for item in osr_lucky:
        item['avg'] = item['count'] / item['six']

    osr_lucky = list(sorted(osr_lucky, key=lambda x: x['avg']))

    if len(osr_lucky) < 20:
        return None

    osr_lucky_rank = {
        'lucky': list(osr_lucky[:10]),
        'unlucky': list(reversed(osr_lucky[-10:])),
        'time': datetime.now()
    }

    return osr_lucky_rank