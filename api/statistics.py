from datetime import datetime
from pydantic import BaseModel
from collections import defaultdict

from api.account_datas import DiamondTotalInfo, DiamondTypeInfo
from api.cache import cached_with_refresh
from api.datas import PoolInfo
from api.users import UserInDB, UserConfig
from api.pydantic_models import UsernameDisplayStatus
from api.models import Account, DBUser, database_manager, OperatorSearchRecord, OSROperator, PayRecord, Platform, DiamondRecord
from api.utils import f_hide_mid


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
        return f'{account.nickname} (Self)'

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
    enable_users: list[DBUser] = list([user for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)) if user.user_config.is_lucky_rank])

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
    return LuckyRankInfo.model_validate(info)


@cached_with_refresh(ttl=3600, key_builder=lambda: 'pool_lucky_rank_info')
async def compute_pool_lucky_rank() -> dict[str, object] | None:
    def get_first_pool_id_of_type(pool_type: str) -> str:
        return next((pool_id for pool_id in pools if PoolInfo.get_pool_info(pool_id)['type'] == pool_type), '')

    enable_users: list[DBUser] = list([user for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)) if user.user_config.is_lucky_rank])

    osr_lucky = defaultdict(lambda: {'six': 0, 'count': 0, 'account': None, 'avg': 0.0})

    pools = PoolInfo.get_now_pools()
    if pools is None:
        return None

    pool: str = ''
    pool_types = ['LINKAGE', 'LIMITED', 'SINGLE', 'NORMAL', 'CLASSIC']
    for pool_type in pool_types:
        if pool := get_first_pool_id_of_type(pool_type):
            break
    if not pool:
        return None

    records = await database_manager.execute(OperatorSearchRecord.select().join_from(OperatorSearchRecord, Account).where(OperatorSearchRecord.pool_id == pool).where(Account.owner.in_(enable_users)))

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
        'pool': pool
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
    return PoolLuckyRankInfo.model_validate(info)


@cached_with_refresh(ttl=3600, key_builder=lambda: 'six_up_rank_info')
async def compute_six_up_rank() -> dict | None:
    enable_users: list[DBUser] = list([user for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)) if user.user_config.is_lucky_rank])
    up_pools = list([k for k, v in PoolInfo.get_all_pools().items() if 'up_char_info' in v])

    osr_up = defaultdict(lambda: {'six': 0, 'not_up': 0, 'account': None, 'avg': 0.0})

    records = await database_manager.execute(
        OperatorSearchRecord.select().where(OperatorSearchRecord.pool_id.in_(up_pools))
        .join_from(OperatorSearchRecord, Account).where(Account.owner.in_(enable_users))
    )

    record: OperatorSearchRecord
    for record in records:
        account = record.account
        osr_up[account.id]['account'] = account

        operator: OSROperator
        for operator in record.operators:
            if operator.rarity == 6 and operator.is_up is not None:
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
    return UPRankInfo.model_validate(info)


@cached_with_refresh(ttl=7200, key_builder=lambda: 'site_statistics')
async def compute_site_statistics() -> dict:
    enable_users: list[DBUser] = list([user for user in await database_manager.execute(DBUser.select().where(DBUser.disabled == False)) if user.user_config.is_statistics])
    accounts = [account for account in await database_manager.execute(Account.select().where(Account.owner.in_(enable_users)))]

    account_number: int = len(accounts)
    available_account_number: int = await database_manager.count(Account.select().where(Account.owner.in_(enable_users)).where(Account.available == True))

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
        'type_use': defaultdict[str, dict[str, object]](lambda: {'type': '', 'number': 0}),
        'type_get': defaultdict[str, dict[str, object]](lambda: {'type': '', 'number': 0})
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

    diamond_info['type_get'] = list(sorted(diamond_info['type_get'].values(), key=lambda x: x['number'], reverse=True))  # noqa
    diamond_info['type_use'] = list(sorted(diamond_info['type_use'].values(), key=lambda x: x['number'], reverse=True))  # noqa

    osr_info = {
        'osr_number_pool': defaultdict[str, int | dict[str, int]](int),
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
        pool_id: str = record.pool_id
        if not pool_id:
            continue

        pool_info = PoolInfo.get_pool_info(pool_id)
        if pool_info['type'] == 'UNKNOWN':
            continue

        pool_name = pool_info.get('name')
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

            if rarity == '6' and 'up_char_info' in pool_info:
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

    osr_info['osr_number_month'] = dict(reversed(osr_info['osr_number_month'].items()))  # noqa

    statistics_info = {
        'account_info': account_info,
        'total_pay_money': total_pay_money,
        'diamond_info': diamond_info,
        'osr_info': osr_info
    }

    return statistics_info


async def get_site_statistics_info() -> SiteStatisticsInfo:
    return SiteStatisticsInfo.model_validate(await compute_site_statistics())
