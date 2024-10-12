from typing import Union

from src.api.arknights_data_request import ArknightsDataRequest, create_request_by_token
from src.api.databases import Account, AccountChannel, OperatorSearchRecord, OSROperator, DiamondRecord, Platform, PayRecord, GiftRecord, database
from src.api.datas import PoolInfo


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

        if not force and await OperatorSearchRecord.select().where(OperatorSearchRecord.account == self.account).aio_count():
            record: OperatorSearchRecord = (await OperatorSearchRecord.select().where(OperatorSearchRecord.account == self.account).order_by(OperatorSearchRecord.time.desc()).limit(1).aio_execute())[0]
            last_time = record.time

        osr_datas: list = await self.request.get_cards_record(last_time)

        async with database.aio_atomic():
            item: dict
            for item in osr_datas:
                time: int = item['ts']
                chars: list = item['chars']
                real_pool: str | None = item['pool']
                pool_id: str | None
                if real_pool == '未知卡池':
                    real_pool = None
                    pool_id = None
                else:
                    pool_id = PoolInfo.get_pool_id_by_info(real_pool, time)

                osr: OperatorSearchRecord
                osr, created = await OperatorSearchRecord.aio_get_or_create(account=self.account, time=time, defaults={'real_pool': real_pool, 'pool_id': pool_id})

                pool_info = PoolInfo.get_pool_info(pool_id)
                is_up_pool = 'up_char_info' in pool_info

                if created:
                    index: int
                    char_item: dict
                    for index, char_item in enumerate(chars):
                        name: str = char_item['name']
                        rarity: int = char_item['rarity'] + 1
                        is_new: bool = char_item['isNew']
                        is_up: bool | None = name in pool_info['up_char_info'] if is_up_pool else None
                        await OSROperator.aio_create(name=name, rarity=rarity, is_new=is_new, index=index, record=osr, is_up=is_up)
                elif pool_id and osr.real_pool != real_pool:
                    osr.real_pool = real_pool
                    osr.pool_id = pool_id
                    await osr.aio_save()

                    if is_up_pool:
                        osr_operator: OSROperator
                        for osr_operator in await OSROperator.select().where(OSROperator.record == osr).aio_execute():
                            osr_operator.is_up = bool(osr_operator.name in pool_info['up_char_info'])
                            await osr_operator.aio_save()

    async def fetch_diamond_record(self) -> None:
        last_time: int = 0
        if await DiamondRecord.select().where(DiamondRecord.account == self.account).aio_count():
            record: DiamondRecord = (await DiamondRecord.select().where(DiamondRecord.account == self.account).order_by(DiamondRecord.operate_time.desc()).limit(1).aio_execute())[0]
            last_time = record.operate_time

        diamond_datas: list = await self.request.get_diamond_record(last_time)

        async with database.aio_atomic():
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

                    await DiamondRecord.aio_get_or_create(
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

        async with database.aio_atomic():
            item: dict
            for item in pay_datas:
                order_id: str = item['orderId']
                name: str = item['productName']
                amount: int = item['amount']
                pay_time: int = int(item['payTime'])
                platform: Platform = Platform.get(item['platform'])

                await PayRecord.aio_get_or_create(
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

        async with database.aio_atomic():
            item: dict
            for item in gift_datas:
                time = item['ts']
                name = item['giftName']
                code = item['code']

                await GiftRecord.aio_get_or_create(
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

            async with database.aio_atomic():
                account, created = await Account.aio_get_or_create(uid=uid, defaults=updates)
                if not created and any(getattr(account, key) != value for key, value in updates.items()):
                    await Account.update(**updates).where(Account.uid == uid).aio_execute()  # 更新数据

                return cls(account, request), created
        except ValueError:
            return None, True

    @classmethod
    async def get_analysis(cls, account: Account) -> Union['ArknightsDataAnalysis', None]:
        analyses: ArknightsDataAnalysis = (await cls.get_or_create_analysis(account.token, account.channel))[0]
        if not analyses:
            account.available = False
            await account.aio_save()
        return analyses
