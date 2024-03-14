from datetime import datetime
from pydantic import BaseModel
from collections import defaultdict

from .account_datas import DiamondTotalInfo, DiamondTypeInfo
from .arknights_data_analysis import get_or_create_osr_pool
from .cache import cached_with_refresh
from .datas import AnalysisData
from .users import UserInDB, UserConfig, UsernameDisplayStatus
from .models import Account, DBUser, database_manager, OperatorSearchRecord, OSROperator, OSRPool, PayRecord, Platform, DiamondRecord
from .utils import f_hide_mid

pool_progress = AnalysisData().get_data()['pool_progress']


class LuckyRankUser(BaseModel):
    name: str
    six: int
    count: int
    avg: float


class LuckyRankInfo(BaseModel):
    lucky: list[LuckyRankUser]
    unlucky: list[LuckyRankUser]
    time: datetime


class PoolLuckyRankInfo(LuckyRankInfo):
    pool: str


class UPRankUser(BaseModel):
    name: str
    six: int
    not_up: int
    avg: float


class UPRankInfo(BaseModel):
    up: list[UPRankUser]
    not_up: list[UPRankUser]
    time: datetime


class SiteAccountInfo(BaseModel):
    account_number: int
    available_account_number: int
    available_avg: float


class SiteDiamondInfo(BaseModel):
    now: dict[Platform, DiamondTotalInfo]
    total_use: dict[Platform, DiamondTotalInfo]
    total_get: dict[Platform, DiamondTotalInfo]
    type_use: list[DiamondTypeInfo]
    type_get: list[DiamondTypeInfo]


class SiteOSRInfo(BaseModel):
    osr_lucky_avg: dict[str, float]
    osr_number_month: dict[str, int]
    osr_number_pool: dict[str, int | dict[str, int]]
    osr_not_up_avg: dict[str, float]


class SiteStatisticsInfo(BaseModel):
    account_info: SiteAccountInfo
    osr_info: SiteOSRInfo
    diamond_info: SiteDiamondInfo
    total_pay_money: int


def get_confined_account_name(user: UserInDB, account: Account) -> str:
    if user.username == account.owner.name:
        return f'{account.nickname} (Owner)'

    username: str
    user_config: UserConfig = account.owner.user_config
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


@cached_with_refresh(ttl=3600, key_builder=lambda: 'lucky_rank_info')
async def compute_lucky_rank() -> dict | None:
    enable_users: list[DBUser] = []

    user: DBUser
    for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)):
        if user.user_config.is_lucky_rank:
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


async def get_lucky_rank_info(user: UserInDB) -> LuckyRankInfo | None:
    info: dict = await compute_lucky_rank()
    if info is None:
        return None

    for item in info['lucky']:
        item['name'] = get_confined_account_name(user, item['account'])
    for item in info['unlucky']:
        item['name'] = get_confined_account_name(user, item['account'])
    return LuckyRankInfo(**info)


@cached_with_refresh(ttl=3600, key_builder=lambda: 'pool_lucky_rank_info')
async def compute_pool_lucky_rank() -> dict | None:
    enable_users: list[DBUser] = []

    user: DBUser
    for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)):
        if user.user_config.is_lucky_rank:
            enable_users.append(user)

    osr_lucky = defaultdict(lambda: {'six': 0, 'count': 0, 'account': None, 'avg': 0.0})

    pool, _ = await get_or_create_osr_pool(pool_progress[-1])
    if pool is None:
        return None

    records = await database_manager.execute(OperatorSearchRecord.select().join_from(OperatorSearchRecord, Account).where(OperatorSearchRecord.pool == pool).where(Account.owner.in_(enable_users)))

    for record in records:
        account = record.account
        osr_lucky[account.id]['account'] = account

        operator: OSROperator
        for operator in record.operators:
            osr_lucky[account.id]['count'] += 1
            if operator.rarity == 6:
                osr_lucky[account.id]['six'] += 1

    osr_lucky = [v for v in osr_lucky.values() if v['six'] > 1]
    for item in osr_lucky:
        item['avg'] = item['count'] / item['six']

    osr_lucky = list(sorted(osr_lucky, key=lambda x: x['avg']))

    if len(osr_lucky) < 20:
        return None

    osr_lucky_rank = {
        'lucky': list(osr_lucky[:10]),
        'unlucky': list(reversed(osr_lucky[-10:])),
        'time': datetime.now(),
        'pool': pool.name
    }

    return osr_lucky_rank


async def get_pool_lucky_rank_info(user: UserInDB) -> PoolLuckyRankInfo | None:
    info: dict = await compute_pool_lucky_rank()
    if info is None:
        return None

    for item in info['lucky']:
        item['name'] = get_confined_account_name(user, item['account'])
    for item in info['unlucky']:
        item['name'] = get_confined_account_name(user, item['account'])
    return PoolLuckyRankInfo(**info)


# noinspection all
@cached_with_refresh(ttl=3600, key_builder=lambda: 'six_up_rank_info')
async def compute_six_up_rank() -> dict | None:
    enable_users: list[DBUser] = []

    user: DBUser
    for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)):
        if user.user_config.is_lucky_rank:
            enable_users.append(user)

    osr_up = defaultdict(lambda: {'six': 0, 'not_up': 0, 'account': None, 'avg': 0.0})

    records = await database_manager.execute(
        OperatorSearchRecord.select().join_from(OperatorSearchRecord, Account).where(Account.owner.in_(enable_users))
        .join_from(OperatorSearchRecord, OSRPool).where(OSRPool.is_up_pool == True)
    )

    record: OperatorSearchRecord
    for record in records:
        account = record.account
        osr_up[account.id]['account'] = account

        operator: OSROperator
        for operator in record.operators:
            if operator.rarity == 6:
                osr_up[account.id]['six'] += 1
                if not operator.is_up:
                    osr_up[account.id]['not_up'] += 1

    osr_up = [v for v in osr_up.values() if v['six'] > 5]
    for item in osr_up:
        item['avg'] = item['not_up'] / item['six']

    osr_up = list(sorted(osr_up, key=lambda x: x['avg']))

    if len(osr_up) < 20:
        return None

    osr_up_info = {
        'up': list(osr_up[:10]),
        'not_up': list(reversed(osr_up[-10:])),
        'time': datetime.now()
    }

    return osr_up_info


async def get_six_up_rank_info(user: UserInDB) -> UPRankInfo | None:
    info: dict = await compute_six_up_rank()
    if info is None:
        return None

    for item in info['up']:
        item['name'] = get_confined_account_name(user, item['account'])
    for item in info['not_up']:
        item['name'] = get_confined_account_name(user, item['account'])
    return UPRankInfo(**info)


# noinspection all
@cached_with_refresh(ttl=7200, key_builder=lambda: 'site_statistics')
async def compute_site_statistics() -> dict:
    enable_users: list[DBUser] = []

    user: DBUser
    for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)):
        if user.user_config.is_statistics:
            enable_users.append(user)

    accounts = [account for account in await database_manager.execute(Account.select().where(Account.owner.in_(enable_users)))]
    account_number = len(accounts)
    available_account_number = await database_manager.count(Account.select().where(Account.owner.in_(enable_users)).where(Account.available == True))

    account_info: dict = {
        'account_number': account_number,
        'available_account_number': available_account_number,
        'available_avg': available_account_number / account_number
    }

    total_pay_money: int = 0

    pay_records = await database_manager.execute(PayRecord.select().where(PayRecord.account.in_(accounts)))
    pay_record: PayRecord
    for pay_record in pay_records:
        total_pay_money += pay_record.amount / 100

    diamond_info = {
        'now': {
            Platform.ANDROID: {'platform': Platform.ANDROID, 'number': 0},
            Platform.IOS: {'platform': Platform.IOS, 'number': 0}
        },
        'total_use': {
            Platform.ANDROID: {'platform': Platform.ANDROID, 'number': 0},
            Platform.IOS: {'platform': Platform.IOS, 'number': 0}
        },
        'total_get': {
            Platform.ANDROID: {'platform': Platform.ANDROID, 'number': 0},
            Platform.IOS: {'platform': Platform.IOS, 'number': 0}
        },
        'type_use': defaultdict(lambda: {'type': '', 'number': 0}),
        'type_get': defaultdict(lambda: {'type': '', 'number': 0})
    }

    for account in accounts:
        diamond_records = await database_manager.execute(DiamondRecord.select().where(DiamondRecord.account == account).order_by(DiamondRecord.operate_time.desc()))
        platform_now = {
            Platform.ANDROID: True,
            Platform.IOS: True
        }

        diamond_record: DiamondRecord
        for diamond_record in diamond_records:
            if platform_now[diamond_record.platform]:
                platform_now[diamond_record.platform] = False
                diamond_info['now'][diamond_record.platform]['number'] = diamond_record.after

            change = diamond_record.after - diamond_record.before
            if change > 0:
                diamond_info['total_get'][diamond_record.platform]['number'] += change
                diamond_info['type_get'][diamond_record.operation]['type'] = diamond_record.operation
                diamond_info['type_get'][diamond_record.operation]['number'] += change
            else:
                diamond_info['total_use'][diamond_record.platform]['number'] -= change
                diamond_info['type_use'][diamond_record.operation]['type'] = diamond_record.operation
                diamond_info['type_use'][diamond_record.operation]['number'] -= change

    diamond_info['type_get'] = list(sorted(diamond_info['type_get'].values(), key=lambda x: x['number'], reverse=True))
    diamond_info['type_use'] = list(sorted(diamond_info['type_use'].values(), key=lambda x: x['number'], reverse=True))

    osr_info = {
        'osr_number_pool': defaultdict(int),
        'osr_number_month': defaultdict(int),
        'osr_lucky': {
            '6': 0, '5': 0, '4': 0, '3': 0,
            'count': {'6': 0, '5': 0, '4': 0, '3': 0}
        },
        'osr_lucky_avg': {'6': 0, '5': 0, '4': 0, '3': 0},
        'osr_not_up': {'total': 0},
        'osr_six': defaultdict(int),
        'osr_not_up_avg': {}
    }

    osr_info['osr_number_pool']['total'] = {'all': 0, '3': 0, '4': 0, '5': 0, '6': 0}

    records = await database_manager.execute(OperatorSearchRecord.select().where(OperatorSearchRecord.account.in_(accounts)).order_by(OperatorSearchRecord.time))
    record: OperatorSearchRecord
    for record in records:
        pool: OSRPool = record.pool
        pool_name = record.pool.name

        operators = record.operators
        operators_number = len(operators)

        osr_info['osr_number_month'][datetime.fromtimestamp(record.time).strftime('%Y-%m')] += operators_number
        osr_info['osr_number_pool'][pool_name] += operators_number
        osr_info['osr_number_pool']['total']['all'] += operators_number

        operator: OSROperator
        for operator in operators:
            rarity = str(operator.rarity)
            osr_info['osr_number_pool']['total'][rarity] += 1

            for r in map(str, range(3, 7)):
                osr_info['osr_lucky']['count'][r] += 1
            osr_info['osr_lucky'][rarity] += 1

            if pool.is_up_pool and rarity == '6':
                if pool_name not in osr_info['osr_not_up']:
                    osr_info['osr_not_up'][pool_name] = 0

                osr_info['osr_six'][pool_name] += 1
                osr_info['osr_six']['total'] += 1
                if not operator.is_up:
                    osr_info['osr_not_up'][pool_name] += 1
                    osr_info['osr_not_up']['total'] += 1

    for r in map(str, range(3, 7)):
        if osr_info['osr_lucky'][r] == 0:
            osr_info['osr_lucky_avg'][r] = 0
        else:
            osr_info['osr_lucky_avg'][r] = osr_info['osr_lucky']['count'][r] / osr_info['osr_lucky'][r]

    for osr_not_up_pool in osr_info['osr_not_up']:
        osr_info['osr_not_up_avg'][osr_not_up_pool] = osr_info['osr_not_up'][osr_not_up_pool] / osr_info['osr_six'][osr_not_up_pool]

    osr_info['osr_number_month'] = dict(reversed(osr_info['osr_number_month'].items()))

    statistics_info = {
        'account_info': account_info,
        'total_pay_money': total_pay_money,
        'diamond_info': diamond_info,
        'osr_info': osr_info
    }

    return statistics_info


async def get_site_statistics_info() -> SiteStatisticsInfo:
    return SiteStatisticsInfo(**(await compute_site_statistics()))
