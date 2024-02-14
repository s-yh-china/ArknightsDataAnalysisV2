from pydantic import BaseModel
from datetime import datetime
from collections import defaultdict

from .models import Account, OperatorSearchRecord, database_manager, OSRPool, OSROperator
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
        'osr_number_pool': dict(osr_number),
        'osr_pool': list(reversed(osr_pool)),
        'osr_not_up_avg': dict(osr_not_up_avg),
        'time': {
            'start_time': str(datetime.fromtimestamp(records[0].time)) if records else 'N/A',
            'end_time': str(datetime.fromtimestamp(records[-1].time)) if records else 'N/A'
        }
    }

    print(osr_info)

    return OSRInfo(**osr_info)
