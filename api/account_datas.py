from fastapi import HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from collections import defaultdict

from .models import database_manager
from .models import Account, OperatorSearchRecord, OSRPool, OSROperator, Platform, PayRecord, DiamondRecord
from .accounts import AccountInDB


class AccountDataTime(BaseModel):
    start_time: datetime
    end_time: datetime


class OSRInfo(BaseModel):
    osr_lucky_avg: dict[str, float]
    osr_lucky_count: dict[str, dict[str, int]]
    osr_number_month: dict[str, int]
    osr_number_pool: dict[str, int | dict[str, int]]
    osr_pool: list[str]
    osr_not_up_avg: dict[str, float]
    time: AccountDataTime

    class Config:
        json_schema_extra = {
            'examples': [
                {'osr_lucky_avg': {'6': 37.4, '5': 11.6875, '4': 2.077777777777778, '3': 2.460526315789474}, 'osr_lucky_count': {'千秋一粟': {'3': 5, '4': 1, '5': 0, '6': 38}, '标准寻访': {'3': 5, '4': 0, '5': 4, '6': 17}}, 'osr_number_month': {'2024-02': 117, '2024-01': 70}, 'osr_number_pool': {'total': {'all': 187, '3': 76, '4': 90, '5': 16, '6': 5}, '一线微明': 70, '千秋一粟': 117}, 'osr_pool': ['千秋一粟', '一线微明'], 'osr_not_up_avg': {'total': 0.2, '一线微明': 0.5, '千秋一粟': 0.0}, 'time': {'start_time': '2024-01-18 12:36:16', 'end_time': '2024-02-07 11:59:13'}}
            ]
        }


class OSROperatorInfo(BaseModel):
    time: datetime
    name: str
    rarity: int
    count: int
    is_new: bool
    is_up: bool | None


class OSRPoolInfo(BaseModel):
    pool: str
    osr_number: dict[str, int]
    osr_lucky_avg: dict[str, float]
    osr_number_day: dict[str, int]
    osr_six_record: list[OSROperatorInfo]
    osr_five_record: list[OSROperatorInfo]

    class Config:
        json_schema_extra = {
            'examples': [
                {'pool': '千秋一粟', 'osr_number': {'3': 53, '4': 53, '5': 8, '6': 3, 'all': 117}, 'osr_lucky_avg': {'3': 2.207547169811321, '4': 2.207547169811321, '5': 14.625, '6': 39}, 'osr_number_day': {'2024-02-07': 1, '2024-02-06': 11, '2024-02-05': 1, '2024-02-04': 11, '2024-02-03': 1, '2024-02-02': 11, '2024-02-01': 81}, 'osr_six_record': [{'time': '2024-02-01T16:07:23', 'name': '黍', 'rarity': 6, 'count': 6, 'is_new': False, 'is_up': True}, {'time': '2024-02-01T16:07:23', 'name': '黍', 'rarity': 6, 'count': 45, 'is_new': False, 'is_up': True}, {'time': '2024-02-01T16:01:56', 'name': '黍', 'rarity': 6, 'count': 28, 'is_new': True, 'is_up': True}],
                 'osr_five_record': [{'time': '2024-02-07T11:59:13', 'name': '灰毫', 'rarity': 5, 'count': 10, 'is_new': False, 'is_up': False}, {'time': '2024-02-06T10:39:03', 'name': '贾维', 'rarity': 5, 'count': 22, 'is_new': False, 'is_up': False}, {'time': '2024-02-02T01:25:31', 'name': '小满', 'rarity': 5, 'count': 14, 'is_new': False, 'is_up': False}, {'time': '2024-02-01T16:07:00', 'name': '小满', 'rarity': 5, 'count': 20, 'is_new': False, 'is_up': False}, {'time': '2024-02-01T16:03:44', 'name': '掠风', 'rarity': 5, 'count': 22, 'is_new': False, 'is_up': False}, {'time': '2024-02-01T16:01:56', 'name': '小满', 'rarity': 5, 'count': 8, 'is_new': False, 'is_up': False}, {'time': '2024-02-01T16:01:46', 'name': '小满', 'rarity': 5, 'count': 11, 'is_new': False, 'is_up': False}, {'time': '2024-02-01T16:01:36', 'name': '小满', 'rarity': 5, 'count': 10, 'is_new': True, 'is_up': False}]}
            ]
        }


class PayInfo(BaseModel):
    time: datetime
    name: str
    amount: int
    platform: Platform


class PayRecordInfo(BaseModel):
    total_money: int
    pay_info: list[PayInfo]


class DiamondTotalInfo(BaseModel):
    platform: Platform
    number: int


class DiamondTypeInfo(BaseModel):
    type: str
    number: int


class DiamondInfo(BaseModel):
    now: dict[Platform, DiamondTotalInfo]
    total_use: dict[Platform, DiamondTotalInfo]
    total_get: dict[Platform, DiamondTotalInfo]
    type_use: list[DiamondTypeInfo]
    type_get: list[DiamondTypeInfo]
    day: dict[str, int]
    time: AccountDataTime


# noinspection all
async def get_osr_info(account: AccountInDB) -> OSRInfo:
    db_account: Account = await account.get_db()

    osr_not_up = {'total': 0}
    osr_six = defaultdict(int)

    osr_number = defaultdict(int)
    osr_number['total'] = {'all': 0, '3': 0, '4': 0, '5': 0, '6': 0}

    osr_lucky = defaultdict(lambda: {'6': [], '5': [], '4': [], '3': [], 'count': defaultdict(int)})
    osr_number_month = defaultdict(int)

    osr_pool = []

    records = await database_manager.execute(OperatorSearchRecord.select().where(OperatorSearchRecord.account == db_account).order_by(OperatorSearchRecord.time))

    record: OperatorSearchRecord
    for record in records:
        pool: OSRPool = record.pool
        pool_type = record.pool.type
        pool_name = record.pool.name

        if pool_name not in osr_pool:
            osr_pool.append(pool_name)

        operators = record.operators
        operators_number = len(operators)

        osr_number_month[datetime.fromtimestamp(record.time).strftime('%Y-%m')] += operators_number
        osr_number[pool_name] += operators_number
        osr_number['total']['all'] += operators_number

        operator: OSROperator
        for operator in operators:
            rarity = str(operator.rarity)
            osr_number['total'][rarity] += 1

            for r in map(str, range(3, 7)):
                osr_lucky[pool_type]['count'][r] += 1

            osr_lucky[pool_type][rarity].append(osr_lucky[pool_type]['count'][rarity])
            osr_lucky[pool_type]['count'][rarity] = 0

            if pool.is_up_pool and rarity == '6':
                if pool_name not in osr_not_up:
                    osr_not_up[pool_name] = 0

                osr_six[pool_name] += 1
                osr_six['total'] += 1
                if not operator.is_up:
                    osr_not_up[pool_name] += 1
                    osr_not_up['total'] += 1

    osr_lucky_avg = {'6': [], '5': [], '4': [], '3': []}
    osr_lucky_count = {}
    osr_lucky_count_pool_num = {'6': 0, '5': 0, '4': 0, '3': 0}
    for osr_lucky_pool in osr_lucky:
        for rarity in map(str, range(3, 7)):
            osr_lucky_avg[rarity].extend(osr_lucky[osr_lucky_pool][rarity])
            if osr_lucky[osr_lucky_pool]['count'][rarity] != 0:
                osr_lucky_avg[rarity].append(osr_lucky[osr_lucky_pool]['count'][rarity])
                osr_lucky_count_pool_num[rarity] += 1
        osr_lucky_count[osr_lucky_pool] = dict(osr_lucky[osr_lucky_pool]['count'])

    for rarity in map(str, range(3, 7)):
        if (len(osr_lucky_avg[rarity]) - osr_lucky_count_pool_num[rarity]) <= 0:
            osr_lucky_avg[rarity] = 0
        else:
            osr_lucky_avg[rarity] = sum(osr_lucky_avg[rarity]) / (len(osr_lucky_avg[rarity]) - osr_lucky_count_pool_num[rarity])

    osr_not_up_avg = {pool: osr_not_up[pool] / osr_six[pool] for pool in osr_not_up if osr_six[pool] > 0} or {'total': 0}

    osr_info = {
        'osr_lucky_avg': osr_lucky_avg,
        'osr_lucky_count': dict(reversed(osr_lucky_count.items())),
        'osr_number_month': dict(reversed(osr_number_month.items())),
        'osr_number_pool': osr_number,
        'osr_pool': list(reversed(osr_pool)),
        'osr_not_up_avg': osr_not_up_avg,
        'time': {
            'start_time': datetime.fromtimestamp(records[0].time) if records else datetime.fromtimestamp(0),
            'end_time': datetime.fromtimestamp(records[-1].time) if records else datetime.fromtimestamp(0)
        }
    }

    return OSRInfo.model_validate(osr_info)


async def get_osr_pool_info(account: AccountInDB, pool_name: str) -> OSRPoolInfo:
    db_account: Account = await account.get_db()
    pool = await database_manager.get_or_none(OSRPool, name=pool_name)

    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pool Not Found"
        )

    osr_number = defaultdict(int)
    osr_lucky = {
        '6': [], '5': [], '4': [], '3': [],
        'count': {'6': 0, '5': 0, '4': 0, '3': 0}
    }

    osr_number_day = defaultdict(int)

    osr_six_record = []
    osr_five_record = []

    records = await database_manager.execute(OperatorSearchRecord.select().where((OperatorSearchRecord.account == db_account) & (OperatorSearchRecord.pool == pool)).order_by(OperatorSearchRecord.time))

    record: OperatorSearchRecord
    for record in records:
        operators = record.operators
        operators_number = len(operators)
        record_time = datetime.fromtimestamp(record.time)

        osr_number_day[record_time.strftime('%Y-%m-%d')] += operators_number
        osr_number['all'] += operators_number

        operator: OSROperator
        for operator in operators:
            rarity = str(operator.rarity)
            osr_number[rarity] += 1

            for r in map(str, range(3, 7)):
                osr_lucky['count'][r] += 1

            if rarity == '6' or rarity == '5':
                operator_info: OSROperatorInfo = OSROperatorInfo(
                    time=record_time, name=operator.name, rarity=operator.rarity, count=osr_lucky['count'][rarity],
                    is_new=operator.is_new, is_up=operator.is_up
                )
                if rarity == '6':
                    osr_six_record.insert(0, operator_info)
                elif rarity == '5':
                    osr_five_record.insert(0, operator_info)

            osr_lucky[rarity].append(osr_lucky['count'][rarity])
            osr_lucky['count'][rarity] = 0

    osr_lucky_avg = {'6': [], '5': [], '4': [], '3': []}

    for rarity in map(str, range(3, 7)):
        values = osr_lucky[rarity]
        count = osr_lucky['count'][rarity]

        if values:
            osr_lucky_avg[rarity] = (sum(values) + count) / len(values)
        else:
            osr_lucky_avg[rarity] = 0

    osr_info = {
        'pool': pool_name,
        'osr_number': osr_number,
        'osr_lucky_avg': osr_lucky_avg,
        'osr_number_day': dict(reversed(osr_number_day.items())),
        'osr_six_record': osr_six_record,
        'osr_five_record': osr_five_record
    }

    return OSRPoolInfo.model_validate(osr_info)


async def get_pay_record_info(account: AccountInDB) -> PayRecordInfo:
    db_account = await account.get_db()

    pay_info = []
    total_money = 0

    pay_records = await database_manager.execute(PayRecord.select().where(PayRecord.account == db_account).order_by(PayRecord.pay_time.desc()))
    pay_record: PayRecord
    for pay_record in pay_records:
        info = PayInfo(time=datetime.fromtimestamp(pay_record.pay_time), name=pay_record.name, amount=pay_record.amount / 100, platform=pay_record.platform)
        pay_info.append(info)
        total_money += pay_record.amount / 100

    return PayRecordInfo(total_money=total_money, pay_info=pay_info)


async def get_diamond_info(account: AccountInDB) -> DiamondInfo:
    db_account = await account.get_db()

    info = {
        'now': {
            Platform.ANDROID: {'platform': Platform.ANDROID, 'number': -1},
            Platform.IOS: {'platform': Platform.IOS, 'number': -1}
        },
        'total_use': {
            Platform.ANDROID: {'platform': Platform.ANDROID, 'number': -1},
            Platform.IOS: {'platform': Platform.IOS, 'number': -1}
        },
        'total_get': {
            Platform.ANDROID: {'platform': Platform.ANDROID, 'number': -1},
            Platform.IOS: {'platform': Platform.IOS, 'number': -1}
        },
        'type_use': defaultdict(lambda: {'type': '', 'number': 0}),
        'type_get': defaultdict(lambda: {'type': '', 'number': 0}),
        'day': defaultdict(int),
    }

    records = await database_manager.execute(DiamondRecord.select().where(DiamondRecord.account == db_account).order_by(DiamondRecord.operate_time.desc()))

    record: DiamondRecord
    for record in records:
        if info['now'][record.platform]['number'] == -1:
            info['now'][record.platform]['number'] = record.after

        change = record.after - record.before

        if change > 0:
            if info['total_get'][record.platform]['number'] == -1:
                info['total_get'][record.platform]['number'] = 0

            info['total_get'][record.platform]['number'] += change
            info['type_get'][record.operation]['number'] += change
            info['type_get'][record.operation]['type'] = record.operation
        else:
            if info['total_use'][record.platform]['number'] == -1:
                info['total_use'][record.platform]['number'] = 0

            info['total_use'][record.platform]['number'] += -change
            info['type_use'][record.operation]['number'] += -change
            info['type_use'][record.operation]['type'] = record.operation

        info['day'][datetime.fromtimestamp(record.operate_time).strftime('%Y-%m-%d')] += change

    info['time'] = {
        'start_time': datetime.fromtimestamp(records[0].operate_time) if records else datetime.fromtimestamp(0),
        'end_time': datetime.fromtimestamp(records[-1].operate_time) if records else datetime.fromtimestamp(0)
    }

    info['type_get'] = list(sorted(info['type_get'].values(), key=lambda x: x['number'], reverse=True))
    info['type_use'] = list(sorted(info['type_use'].values(), key=lambda x: x['number'], reverse=True))

    return DiamondInfo(**info)
