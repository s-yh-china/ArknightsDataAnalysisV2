from fastapi import HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from collections import defaultdict

from src.api.datas import PoolInfo
from src.api.databases import Account, OperatorSearchRecord, OSROperator, Platform, PayRecord, DiamondRecord
from src.api.accounts import AccountInDB
from src.api.models import PoolInfoModel


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


class OSROperatorInfo(BaseModel):
    time: datetime
    name: str
    rarity: int
    count: int
    is_new: bool
    is_up: bool | None


class OSRPoolInfo(BaseModel):
    pool_info: PoolInfoModel
    osr_number: dict[str, int]
    osr_lucky_avg: dict[str, float]
    osr_number_day: dict[str, int]
    osr_six_record: list[OSROperatorInfo]
    osr_five_record: list[OSROperatorInfo]


class PayInfo(BaseModel):
    time: datetime
    name: str
    amount: int
    platform: Platform


class PayRecordInfo(BaseModel):
    total_money: int
    pay_info: list[PayInfo]


class DiamondTypeInfo(BaseModel):
    type: str
    number: int


class DiamondInfo(BaseModel):
    now: int
    total_use: int
    total_get: int
    type_use: list[DiamondTypeInfo]
    type_get: list[DiamondTypeInfo]
    day: dict[str, int]
    time: AccountDataTime


async def get_osr_info(account: AccountInDB) -> OSRInfo:
    db_account: Account = await account.get_db()

    osr_not_up = {'total': 0}
    osr_six = defaultdict[str, int](int)

    osr_number = defaultdict[str, int | dict[str, int]](int)
    osr_number['total'] = {'all': 0, '3': 0, '4': 0, '5': 0, '6': 0}

    osr_lucky = defaultdict(lambda: {'6': [], '5': [], '4': [], '3': [], 'count': defaultdict[str, int](int)})
    osr_number_month = defaultdict[str, int](int)

    osr_pool: list[str] = []

    records = await OperatorSearchRecord.select().where(OperatorSearchRecord.account == db_account).order_by(OperatorSearchRecord.time).aio_execute()

    record: OperatorSearchRecord
    for record in records:
        pool_id: str = record.pool_id
        if not pool_id:
            continue

        pool_info = PoolInfo.get_pool_info(pool_id)
        if pool_info['type'] == 'UNKNOWN':
            continue

        pool_type: str = PoolInfo.get_pool_count_type(pool_info)
        if pool_id not in osr_pool:
            osr_pool.append(pool_id)

        operators = await OSROperator.select().where(OSROperator.record == record).aio_execute()
        operators_number = len(operators)

        osr_number_month[datetime.fromtimestamp(record.time).strftime('%Y-%m')] += operators_number
        osr_number[pool_id] += operators_number
        osr_number['total']['all'] += operators_number

        operator: OSROperator
        for operator in operators:
            rarity = str(operator.rarity)
            osr_number['total'][rarity] += 1

            for r in map(str, range(3, 7)):
                osr_lucky[pool_type]['count'][r] += 1

            osr_lucky[pool_type][rarity].append(osr_lucky[pool_type]['count'][rarity])
            osr_lucky[pool_type]['count'][rarity] = 0

            if rarity == '6' and 'up_char_info' in pool_info:
                if pool_id not in osr_not_up:
                    osr_not_up[pool_id] = 0

                osr_six[pool_id] += 1
                osr_six['total'] += 1
                if not operator.is_up:
                    osr_not_up[pool_id] += 1
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


async def get_osr_pool_info(account: AccountInDB, pool_id: str) -> OSRPoolInfo:
    db_account: Account = await account.get_db()

    pool_info = PoolInfo.get_pool_info(pool_id)

    if pool_info['type'] == 'UNKNOWN':
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

    records = await OperatorSearchRecord.select().where((OperatorSearchRecord.account == db_account) & (OperatorSearchRecord.pool_id == pool_id)).order_by(OperatorSearchRecord.time).aio_execute()

    record: OperatorSearchRecord
    for record in records:
        operators = await OSROperator.select().where(OSROperator.record == record).aio_execute()
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
        'pool_info': pool_info,
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

    pay_records = await PayRecord.select().where(PayRecord.account == db_account).order_by(PayRecord.pay_time.desc()).aio_execute()
    pay_record: PayRecord
    for pay_record in pay_records:
        info = PayInfo(time=datetime.fromtimestamp(pay_record.pay_time), name=pay_record.name, amount=pay_record.amount / 100, platform=pay_record.platform)
        pay_info.append(info)
        total_money += pay_record.amount / 100

    return PayRecordInfo(total_money=total_money, pay_info=pay_info)


async def get_diamond_info(account: AccountInDB) -> DiamondInfo:
    db_account = await account.get_db()

    info: dict = {
        'now': None,
        'total_use': 0,
        'total_get': 0,
        'type_use': defaultdict[str, dict[str, object]](lambda: {'type': '', 'number': 0}),
        'type_get': defaultdict[str, dict[str, object]](lambda: {'type': '', 'number': 0}),
        'day': defaultdict(int),
    }

    records = await DiamondRecord.select().where(DiamondRecord.account == db_account).order_by(DiamondRecord.operate_time.desc()).aio_execute()

    record: DiamondRecord
    for record in records:
        if info['now'] is None:
            info['now'] = record.after

        change = record.after - record.before

        if change > 0:
            info['total_get'] += change
            info['type_get'][record.operation]['number'] += change
            info['type_get'][record.operation]['type'] = record.operation
        else:
            info['total_use'] -= change
            info['type_use'][record.operation]['number'] -= change
            info['type_use'][record.operation]['type'] = record.operation

        info['day'][datetime.fromtimestamp(record.operate_time).strftime('%Y-%m-%d')] += change

    info['time'] = {
        'start_time': datetime.fromtimestamp(records[0].operate_time) if records else datetime.fromtimestamp(0),
        'end_time': datetime.fromtimestamp(records[-1].operate_time) if records else datetime.fromtimestamp(0)
    }

    info['type_get'] = list(sorted(info['type_get'].values(), key=lambda x: x['number'], reverse=True))
    info['type_use'] = list(sorted(info['type_use'].values(), key=lambda x: x['number'], reverse=True))

    return DiamondInfo.model_validate(info)
