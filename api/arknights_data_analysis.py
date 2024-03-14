import asyncio
from typing import Union

from .arknights_data_request import ArknightsDataRequest, create_request_by_token
from .models import Account, AccountChannel, OSRPool, OperatorSearchRecord, OSROperator, DiamondRecord, Platform, PayRecord, GiftRecord
from .models import database_manager
from .datas import AnalysisData

analysis_data = AnalysisData().get_data()


async def get_or_create_osr_pool(pool_name: str) -> tuple[OSRPool, bool]:
    defaults: dict = analysis_data.get('pool').get(pool_name)

    if defaults:
        defaults.update({'is_auto': False})
    else:
        defaults = {'type': f'{pool_name}', 'is_auto': True}

    pool: OSRPool
    pool, _ = await database_manager.get_or_create(OSRPool, name=pool_name, defaults=defaults)

    if not defaults['is_auto'] and pool.is_auto:
        await database_manager.execute(OSRPool.update(**defaults).where(OSRPool.name == pool_name))
        pool, _ = await database_manager.get_or_create(OSRPool, name=pool_name, defaults=defaults)
        return pool, True

    return pool, False


class ArknightsDataAnalysis:
    def __init__(self, account: Account, request: ArknightsDataRequest) -> None:
        self.account: Account = account
        self.request: ArknightsDataRequest = request

    async def fetch_data(self, force: bool = False) -> None:
        try:
            await self.fetch_osr(force)
            await self.fetch_diamond_record()
            await self.fetch_pay_record()
            await self.fetch_gift_record()
        except ValueError as e:
            print(f'ERROR::{e}')

    async def fetch_osr(self, force: bool = False) -> None:
        last_time: int = 0

        if not force and await database_manager.count(OperatorSearchRecord.select().where(OperatorSearchRecord.account == self.account)):
            record: OperatorSearchRecord = await database_manager.get_or_none(OperatorSearchRecord.select(OperatorSearchRecord.account == self.account).where().order_by(OperatorSearchRecord.time.desc()).first())
            last_time = record.time

        osr_datas: list = await self.request.get_cards_record(last_time)
        update_pool: list = []

        async with database_manager.transaction():
            item: dict
            for item in osr_datas:
                time: int = item['ts']
                pool_name: str = item['pool']
                chars: list = item['chars']

                pool: OSRPool
                updated: bool
                pool, updated = await get_or_create_osr_pool(pool_name)

                if updated and pool not in update_pool:
                    update_pool.append(pool)

                osr: OperatorSearchRecord
                created: bool
                osr, created = await database_manager.get_or_create(OperatorSearchRecord, account=self.account, time=time, defaults={'pool': pool})

                if osr.pool != pool:
                    osr.pool = pool
                    await database_manager.update(osr)

                if created:
                    index: int
                    char_item: dict
                    for index, char_item in enumerate(chars):
                        name: str = char_item['name']
                        rarity: int = char_item['rarity'] + 1
                        is_new: bool = char_item['isNew']
                        is_up: bool | None = name in pool.up_operators if not pool.is_auto and pool.is_up_pool else None

                        await database_manager.create(OSROperator, name=name, rarity=rarity, is_new=is_new, index=index, record=osr, is_up=is_up)
        if len(update_pool) > 0:
            for pool in update_pool:
                task = asyncio.create_task(self.refresh_pool(pool))

    @staticmethod
    async def refresh_pool(pool: OSRPool) -> None:
        if pool.is_auto or not pool.is_up_pool:
            return
        async with database_manager.transaction():
            osr: OperatorSearchRecord
            for osr in await database_manager.execute(OperatorSearchRecord.select().where(OperatorSearchRecord.pool == pool)):
                char_item: OSROperator
                for char_item in await database_manager.execute(OSROperator.select().where(OSROperator.record == osr).where(OSROperator.is_up.is_null(True))):
                    is_up: bool = char_item.name in pool.up_operators
                    char_item.is_up = is_up
                    await database_manager.update(char_item)

    async def fetch_diamond_record(self) -> None:
        last_time: int = 0
        if await database_manager.count(DiamondRecord.select().where(DiamondRecord.account == self.account)):
            record: DiamondRecord = await database_manager.get_or_none(DiamondRecord.select().where(DiamondRecord.account == self.account).order_by(DiamondRecord.operate_time.desc()).first())
            last_time = record.operate_time

        diamond_datas: list = await self.request.get_diamond_record(last_time)

        async with database_manager.transaction():
            item: dict
            for item in diamond_datas:
                time: int = item['ts']
                operation: str = item['operation']
                changes: list = item['changes']

                change_item: dict
                for change_item in changes:
                    platform: Platform = Platform.get(change_item['type'])
                    before: int = change_item['before']
                    after: int = change_item['after']

                    await database_manager.get_or_create(
                        DiamondRecord,
                        account=self.account,
                        operate_time=time,
                        defaults={
                            'operation': operation,
                            'platform': platform,
                            'before': before,
                            'after': after
                        }
                    )

    async def fetch_pay_record(self) -> None:
        pay_datas: list = await self.request.get_pay_record()

        async with database_manager.transaction():
            item: dict
            for item in pay_datas:
                order_id: str = item['orderId']
                name: str = item['productName']
                amount: int = item['amount']
                pay_time: int = int(item['payTime'])
                platform: Platform = Platform.get(item['platform'])

                await database_manager.get_or_create(
                    PayRecord,
                    order_id=order_id,
                    defaults={
                        'name': name,
                        'pay_time': pay_time,
                        'account': self.account,
                        'platform': platform,
                        'amount': amount
                    }
                )

    async def fetch_gift_record(self) -> None:
        gift_datas: list = await self.request.get_gift_record()

        async with database_manager.transaction():
            item: dict
            for item in gift_datas:
                time = item['ts']
                name = item['giftName']
                code = item['code']

                await database_manager.get_or_create(
                    GiftRecord,
                    account=self.account,
                    gift_time=time,
                    defaults={
                        'name': name,
                        'code': code
                    }
                )

    @classmethod
    async def get_or_create_analysis(cls, token: str, channel: AccountChannel) -> tuple['ArknightsDataAnalysis', bool] | tuple[None, bool]:
        request: ArknightsDataRequest = create_request_by_token(token, channel)
        try:
            user_info: dict = await request.get_user_info()
            uid: str = user_info.get('uid')
            updates: dict = {
                'token': token,
                'channel': channel,
                'nickname': user_info.get('nickName'),
                'available': True
            }

            async with database_manager.transaction():
                account, created = await database_manager.get_or_create(Account, uid=uid, defaults=updates)
                if not created and any(getattr(account, key) != value for key, value in updates.items()):
                    await database_manager.execute(Account.update(**updates).where(Account.uid == uid))  # 更新数据

                return cls(account, request), created
        except ValueError:
            return None, True

    @classmethod
    async def get_analysis(cls, account: Account) -> Union['ArknightsDataAnalysis', None]:
        analyses: ArknightsDataAnalysis = (await cls.get_or_create_analysis(account.token, account.channel))[0]
        if not analyses:
            account.available = False
            await database_manager.update(analyses)
        return analyses
