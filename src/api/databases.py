import json

from enum import Enum
from typing import Any

from peewee import DoesNotExist
from peewee import CharField, BooleanField, ForeignKeyField, IntegerField, TimestampField, AutoField
from playhouse.migrate import MySQLMigrator, migrate
from playhouse.mysql_ext import JSONField
from playhouse.shortcuts import ReconnectMixin

from peewee_async import AioModel
from peewee_async import PooledMySQLDatabase as AsyncPooledMySQLDatabase

from src.config import conf, ConfigData
from src.api.models import UserConfig


class ReconnectAsyncPooledMySQLDatabase(ReconnectMixin, AsyncPooledMySQLDatabase):
    _instance = None

    @classmethod
    def get_db_instance(cls, *db_arg, **db_config):
        if not cls._instance:
            cls._instance = cls(*db_arg, **db_config, max_connections=100)
        return cls._instance


database = ReconnectAsyncPooledMySQLDatabase.get_db_instance(**conf.mysql.model_dump())
database.set_allow_sync(False)


class BaseModel(AioModel):
    id = AutoField()

    class Meta:
        database = database


class EnumField(CharField):
    def __init__(self, enum: type[Enum], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.enum = enum

    def db_value(self, value: Any) -> Any:
        return value.value

    def python_value(self, value: Any) -> Any:
        return self.enum(value)


class CJSONField(JSONField):
    def __init__(self, **kwargs: Any) -> None:
        def dump(obj, **kwargs: Any):
            return json.dumps(obj, ensure_ascii=False, **kwargs)

        super().__init__(json_dumps=dump, **kwargs)


class UserConfigField(CJSONField):
    def python_value(self, value: Any) -> UserConfig:
        return UserConfig.model_validate_json(super().python_value(value))


class OnlyTimestampField(TimestampField):
    def python_value(self, value: Any) -> int:
        return value


class DBUser(BaseModel):
    username = CharField(max_length=20, unique=True)
    email = CharField(max_length=30, unique=True)
    hashed_password = CharField(max_length=60)
    user_config = UserConfigField()
    disabled = BooleanField(default=False)


class AccountChannel(str, Enum):
    def __new__(cls, _value: str, _channel_id: int):
        _obj = str.__new__(cls, _value)
        _obj._value_ = _value
        _obj.channel_id = _channel_id
        return _obj

    OFFICIAL = ('OFFICIAL', 1)
    BILIBILI = ('BILIBILI', 2)

    @classmethod
    def get(cls, channel: int | str):
        member: AccountChannel
        for member in cls:
            if member.value == channel or member.channel_id == channel:
                return member
        raise ValueError(f"No member with value or name '{channel}' in {cls.__name__}")


class Account(BaseModel):
    uid = CharField(max_length=20, unique=True)
    owner = ForeignKeyField(DBUser, backref='ark_accs', null=True)
    nickname = CharField(max_length=50)
    token = CharField(max_length=300)
    channel = EnumField(AccountChannel)
    available = BooleanField()

    @classmethod
    async def aio_get_by_uid(cls, uid: str):
        try:
            return await cls.select(cls, DBUser).join(DBUser).where(Account.uid == uid).aio_get()
        except DoesNotExist:
            return None


class OperatorSearchRecord(BaseModel):
    account = ForeignKeyField(Account, backref='card_records')
    real_pool = CharField(null=True)
    pool_id = CharField(null=True)
    time = OnlyTimestampField()


class OSROperator(BaseModel):
    record = ForeignKeyField(OperatorSearchRecord, backref='operators')
    index = IntegerField()
    name = CharField(max_length=10)
    rarity = IntegerField()
    is_new = BooleanField()
    is_up = BooleanField(null=True)


class Platform(str, Enum):
    def __new__(cls, _value: str, _platform_id: int):
        _obj = str.__new__(cls, _value)
        _obj._value_ = _value
        _obj.platform_id = _platform_id
        return _obj

    ANDROID = ('Android', 1)
    IOS = ('iOS', 0)
    ALL = ('all', 2)

    @classmethod
    def get(cls, platform: int | str):
        member: Platform
        for member in cls:
            if member.value == platform or member.platform_id == platform:
                return member
        raise ValueError(f"No member with value or name '{platform}' in {cls.__name__}")


class PayRecord(BaseModel):
    order_id = CharField(unique=True)
    name = CharField()
    account = ForeignKeyField(Account, backref='pay_records')
    pay_time = OnlyTimestampField()
    platform = EnumField(Platform)
    amount = IntegerField()


class DiamondRecord(BaseModel):
    account = ForeignKeyField(Account, backref='diamond_records')
    operation = CharField()
    platform = EnumField(Platform)
    operate_time = OnlyTimestampField()
    before = IntegerField()
    after = IntegerField()


class GiftRecord(BaseModel):
    account = ForeignKeyField(Account, backref='gift_records')
    name = CharField()
    gift_time = OnlyTimestampField()
    code = CharField()


def migrator_database(version: str, migrator: MySQLMigrator):
    pass


with database.allow_sync():
    database_version = ConfigData.get_and_update_database_version()
    if database_version != ConfigData.database_version:
        migrator_database(database_version, MySQLMigrator(database))
    database.create_tables([DBUser, Account, OperatorSearchRecord, OSROperator, PayRecord, DiamondRecord, GiftRecord])
