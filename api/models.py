import json
from enum import Enum
from typing import Any

from peewee import DatabaseProxy, CharField, BooleanField, ForeignKeyField, IntegerField, TimestampField
from playhouse.mysql_ext import JSONField
from playhouse.shortcuts import ReconnectMixin

from peewee_async import Manager, AioModel  # noqa
from peewee_async import PooledMySQLDatabase as AsyncPooledMySQLDatabase

from api.datas import ConfigData
from api.pydantic_models import UserConfig

database_proxy: DatabaseProxy = DatabaseProxy()
database_manager = Manager(database_proxy)


class BaseModel(AioModel):
    class Meta:
        database = database_proxy
        objects = database_manager


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
    slat = CharField(max_length=32)
    user_config = UserConfigField()
    disabled = BooleanField(default=False)


class AccountChannel(str, Enum):
    def __new__(cls, _value: str, channel_id: int):
        _obj = str.__new__(cls, _value)
        _obj._value_ = _value
        _obj.channel_id = channel_id
        return _obj

    OFFICIAL = ('OFFICIAL', 1)
    BILIBILI = ('BILIBILI', 2)


class Account(BaseModel):
    uid = CharField(max_length=20, unique=True)
    owner = ForeignKeyField(DBUser, backref='ark_accs', null=True)
    nickname = CharField(max_length=50)
    token = CharField(max_length=300)
    channel = EnumField(AccountChannel)
    available = BooleanField()


class OperatorSearchRecord(BaseModel):
    account = ForeignKeyField(Account, backref='card_records')
    real_pool = CharField(null=True)
    pool_id = CharField(null=True)
    time = OnlyTimestampField()


class OSROperator(BaseModel):
    record = ForeignKeyField(OperatorSearchRecord, backref='operators')
    name = CharField(max_length=10)
    rarity = IntegerField()
    is_new = BooleanField()
    is_up = BooleanField(null=True)
    index = IntegerField()


class Platform(str, Enum):
    def __new__(cls, _value: str, platform_id: int):
        _obj = str.__new__(cls, _value)
        _obj._value_ = _value
        _obj.platform_id = platform_id
        return _obj

    ANDROID = ('Android', 1)
    IOS = ('iOS', 2)

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


class ReconnectAsyncPooledMySQLDatabase(ReconnectMixin, AsyncPooledMySQLDatabase):
    _instance = None

    @classmethod
    def get_db_instance(cls, *db_arg, **db_config):
        if not cls._instance:
            cls._instance = cls(*db_arg, **db_config, max_connections=100)
        return cls._instance


database_proxy.initialize(ReconnectAsyncPooledMySQLDatabase.get_db_instance(**ConfigData.get_mysql()))
database_proxy.create_tables([DBUser, Account, OperatorSearchRecord, OSROperator, PayRecord, DiamondRecord, GiftRecord])
