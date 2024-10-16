import asyncio
import logging

from datetime import datetime

from peewee import CharField, BooleanField, ForeignKeyField, IntegerField, DateTimeField, AutoField
from peewee_async import AioModel

from src.api.databases import ReconnectAsyncPooledMySQLDatabase, AccountChannel, Platform
from src.api.databases import Account as NewAccount, OperatorSearchRecord as NewOperatorSearchRecord, OSROperator as NewOSROperator
from src.api.databases import DiamondRecord as NewDiamondRecord, PayRecord as NewPayRecord, GiftRecord as NewGiftRecord
from src.api.arknights_data_analysis import ArknightsDataAnalysis
from src.api.datas import PoolInfo

old_database_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': '',
    'port': 3306
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

old_database = ReconnectAsyncPooledMySQLDatabase(**old_database_config)
old_database.set_allow_sync(False)


class OnlyDateTimeField(DateTimeField):
    def python_value(self, value: datetime | int) -> int:
        if isinstance(value, datetime):
            return int(value.timestamp())
        return value


class OldBaseModel(AioModel):
    id = AutoField()

    class Meta:
        database = old_database


class Account(OldBaseModel):
    uid = CharField(max_length=20, unique=True)
    nickname = CharField(max_length=50)
    token = CharField(max_length=300)
    channel = CharField(max_length=2)


class OSRPool(OldBaseModel):
    name = CharField(max_length=20, unique=True)
    type = CharField()


class OperatorSearchRecord(OldBaseModel):
    account = ForeignKeyField(Account, backref='records')
    time = OnlyDateTimeField()
    pool = ForeignKeyField(OSRPool, backref='records')


class OSROperator(OldBaseModel):
    name = CharField(max_length=10)
    rarity = IntegerField()
    is_new = BooleanField()
    index = IntegerField()
    record = ForeignKeyField(OperatorSearchRecord, backref='operators')


class PayRecord(OldBaseModel):
    name = CharField()
    pay_time = OnlyDateTimeField()
    account = ForeignKeyField(Account, backref='pay_records')
    platform = CharField()
    order_id = CharField(unique=True)
    amount = IntegerField()


class DiamondRecord(OldBaseModel):
    account = ForeignKeyField(Account, backref='diamond_records')
    operation = CharField()
    platform = CharField()
    operate_time = OnlyDateTimeField()
    before = IntegerField()
    after = IntegerField()


class GiftRecord(OldBaseModel):
    account = ForeignKeyField(Account, backref='gift_records')
    time = OnlyDateTimeField()
    code = CharField()
    name = CharField()


async def move():
    async def old_account_to_new(old_account: Account) -> tuple[Account, NewAccount]:
        new_account = await NewAccount.aio_create(
            uid=old_account.uid,
            nickname=old_account.nickname,
            token=old_account.token,
            channel=AccountChannel.get(int(old_account.channel)),  # noqa
            available=True
        )
        await ArknightsDataAnalysis.get_analysis(new_account)  # 刷新数据
        return old_account, new_account

    old_accounts = await Account.select().aio_execute()
    new_accounts = await asyncio.gather(*(old_account_to_new(old_account) for old_account in old_accounts))
    logger.info(f'All Account({len(new_accounts)}) moved')

    async def old_osr_to_new(account: NewAccount | None, old_osr: OperatorSearchRecord):
        if account is None:
            print(f'OperatorSearchRecord({old_osr.id}) cant found account')
            return

        real_pool: str | None = old_osr.pool.name
        if old_osr.pool.name == '未知卡池':
            real_pool = None
            pool_id = None
        else:
            pool_id = PoolInfo.get_pool_id_by_info(real_pool, old_osr.time)  # noqa

        new_osr = await NewOperatorSearchRecord.aio_create(
            account=account,
            time=old_osr.time,
            real_pool=real_pool,
            pool_id=pool_id
        )

        pool_info = PoolInfo.get_pool_info(pool_id)
        is_up_pool = 'up_char_info' in pool_info

        operators = await OSROperator.select().where(OSROperator.record == old_osr).aio_execute()
        for operator in operators:
            await NewOSROperator.aio_create(
                name=operator.name,
                rarity=operator.rarity,
                is_new=operator.is_new,
                index=operator.index,
                record=new_osr,
                is_up=operator.name in pool_info['up_char_info'] if is_up_pool else None
            )

    async def old_pay_to_new(account: NewAccount, old_pay: PayRecord):
        await NewPayRecord.aio_create(
            order_id=old_pay.order_id,
            name=old_pay.name,
            account=account,
            pay_time=old_pay.pay_time,
            platform=Platform.get(int(old_pay.platform)),  # noqa
            amount=old_pay.amount
        )

    async def old_diamond_to_new(account: NewAccount, old_diamond: DiamondRecord):
        await NewDiamondRecord.aio_create(
            account=account,
            operation=old_diamond.operation,
            platform=Platform.get(old_diamond.platform),  # noqa
            operate_time=old_diamond.operate_time,
            before=old_diamond.before,
            after=old_diamond.after
        )

    async def old_gift_to_new(account: NewAccount, old_gift: GiftRecord):
        await NewGiftRecord.aio_create(
            account=account,
            gift_time=old_gift.time,
            code=old_gift.code,
            name=old_gift.name
        )

    async def pre_account_move(account: Account, new_account: NewAccount):
        try:
            old_osrs = await OperatorSearchRecord.select(OperatorSearchRecord, OSRPool).join(OSRPool).where(OperatorSearchRecord.account == account).aio_execute()
            await asyncio.wait([asyncio.create_task(old_osr_to_new(new_account, old_osr)) for old_osr in old_osrs])
            logger.info(f'Account({account.uid}) OperatorSearchRecord moved')
        except (ValueError, AssertionError):
            logger.info(f'Account({account.uid}) no OperatorSearchRecord')
        try:
            old_pays = await PayRecord.select().where(PayRecord.account == account).aio_execute()
            await asyncio.wait([asyncio.create_task(old_pay_to_new(new_account, old_pay)) for old_pay in old_pays])
            logger.info(f'Account({account.uid}) PayRecord moved')
        except (ValueError, AssertionError):
            logger.info(f'Account({account.uid}) no PayRecord')
        try:
            old_diamonds = await DiamondRecord.select().where(DiamondRecord.account == account).aio_execute()
            await asyncio.wait([asyncio.create_task(old_diamond_to_new(new_account, old_diamond)) for old_diamond in old_diamonds])
            logger.info(f'Account({account.uid}) DiamondRecord moved')
        except (ValueError, AssertionError):
            logger.info(f'Account({account.uid}) no DiamondRecord')
        try:
            old_gifts = await GiftRecord.select().where(GiftRecord.account == account).aio_execute()
            await asyncio.wait((asyncio.create_task(old_gift_to_new(new_account, old_gift)) for old_gift in old_gifts))
            logger.info(f'Account({account.uid}) GiftRecord moved')
        except (ValueError, AssertionError):
            logger.info(f'Account({account.uid}) no GiftRecord')

    await asyncio.wait([asyncio.create_task(pre_account_move(old_account, new_account)) for old_account, new_account in new_accounts])


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(move())
    loop.close()
