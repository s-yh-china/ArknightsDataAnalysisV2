import json
import base64
import asyncio

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import HTTPException, status

from src.api.accounts import AccountInDB
from src.api.databases import database, OperatorSearchRecord, Account, OSROperator, Platform, PayRecord
from src.api.datas import PoolInfo
from src.logger import logger

with open("data/arkgacha_public_key.pem", "rb") as key_file:
    public_key = serialization.load_pem_public_key(key_file.read())


def verify_signature(data: dict, signature: str) -> bool:
    json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    try:
        public_key.verify(base64.b64decode(signature), json_str.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        logger.warning(f'verify signature error: {e}')
        return False


async def __gacha_data_import(data: dict[str, dict[str, str | list[list[str | int]]]], account: AccountInDB):
    db_account: Account = await account.get_db()
    async with database.aio_atomic():
        for time, item in data.items():
            time: int = int(time)
            chars: list[list[str | int]] = item.get('c')
            real_pool: str | None = PoolInfo.pool_name_fix(item.get('p'))
            pool_id: str | None
            if real_pool == '未知卡池':
                real_pool = None
                pool_id = None
            else:
                pool_id = PoolInfo.get_pool_id_by_info(real_pool, time)

            osr: OperatorSearchRecord
            osr, created = await OperatorSearchRecord.aio_get_or_create(account=db_account, time=time, defaults={'real_pool': real_pool, 'pool_id': pool_id})

            pool_info = PoolInfo.get_pool_info(pool_id)
            is_up_pool = 'up_char_info' in pool_info

            if created:
                index: int
                char_item: dict
                for index, char_item in enumerate(chars):
                    name: str = char_item[0]
                    rarity: int = char_item[1] + 1
                    is_new: bool = bool(char_item[2])
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


async def __pay_data_import(data: dict[str, dict[str, str | int]], account: AccountInDB):
    account: Account = await account.get_db()
    async with database.aio_atomic():
        item: dict
        for time, item in data.items():
            order_id: str = item['orderId']
            name: str = item['productName']
            amount: int = item['amount']
            pay_time: int = int(time)
            platform: Platform = Platform.get(item['platform'])

            await PayRecord.aio_get_or_create(
                order_id=order_id,
                defaults={
                    'name': name,
                    'pay_time': pay_time,
                    'account': account,
                    'platform': platform,
                    'amount': amount
                }
            )


async def data_import(data: bytes, account: AccountInDB):
    try:
        data: dict = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='arkgacha_import.file_not_json'
        )
    if info := data.get('info'):
        if not isinstance(info, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='arkgacha_import.no_info'
            )
        if verify := info.get('verify'):
            del data['info']['verify']
            if not verify_signature(data, verify):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='arkgacha_import.invalid_signature'
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='arkgacha_import.miss_signature'
            )

        match info.get('export_type'):
            case 'gacha':
                _ = asyncio.create_task(__gacha_data_import(data.get('data'), account))
            case 'pay':
                _ = asyncio.create_task(__pay_data_import(data.get('data'), account))
            case _:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='arkgacha_import.unsupported_export_type'
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='arkgacha_import.no_info'
        )
