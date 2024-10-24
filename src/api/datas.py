import os
import json
from typing import override

from httpx import get as http_get
from intervaltree import IntervalTree

from src.config import conf


class JsonData:
    data: dict = {}
    data_file: str

    @classmethod
    def init(cls) -> bool:
        if not hasattr(cls, 'data_file'):
            from src.logger import logger
            logger.critical(f'{cls.__name__} data_file not set')
            exit(1)
        if not os.path.exists(cls.data_file):
            cls.update_data()
            cls.load_data()
            return True
        else:
            cls.load_data()
            return False

    @classmethod
    def load_data(cls) -> dict:
        with open(cls.data_file, 'r', encoding='utf-8') as json_file:
            cls.data = json.load(json_file)
        return cls.data

    @classmethod
    def update_data(cls) -> bool:
        with open(cls.data_file, 'w', encoding='utf-8') as json_file:
            json_file.write(json.dumps(cls.data, indent=4, ensure_ascii=False))
        return True

    @classmethod
    def get_data(cls) -> dict:
        return cls.data


class PoolInfo(JsonData):
    __time_tree: IntervalTree
    pool_name_to_id: dict[str, list[str]]

    data_file = 'data/pool_info.json'

    @classmethod
    @override
    def init(cls) -> bool:
        is_create = super().init()
        if not is_create:
            cls.update_data()
        return is_create

    @classmethod
    @override
    def load_data(cls) -> dict:
        super().load_data()
        cls.__time_tree = IntervalTree()
        cls.pool_name_to_id = {}
        for pool in cls.data['pool'].values():
            cls.__time_tree[pool['start']:pool['end'] + 1] = pool
            if pool['real_name'] not in cls.pool_name_to_id:
                cls.pool_name_to_id[pool['real_name']] = []
            cls.pool_name_to_id[pool['real_name']].append(pool['id'])
        return cls.data

    @classmethod
    @override
    def update_data(cls) -> bool:
        try:
            cls.data = http_get(conf.analysis.pool_info_url).json()
        except Exception as e:
            from src.logger import logger
            logger.warning(f'Update PoolInfo Error: {e}')
            return False
        super().update_data()
        cls.load_data()
        return True

    @classmethod
    def get_all_pools(cls) -> dict[str, dict[str, str | int | dict[str, int] | list[str]]]:
        return cls.data['pool']

    @classmethod
    def get_pool_info(cls, pool_id: str | None) -> dict[str, str | int | dict[str, int] | list[str]]:
        if pool_id is not None:
            if pool_info := cls.data['pool'].get(pool_id):
                return pool_info
        return {
            "id": "UNKNOWN_0_1_1",
            "name": "未知寻访",
            "real_name": "未知寻访",
            "type": "UNKNOWN",
            "start": 0,
            "end": 0
        }

    @classmethod
    def get_pool_id_by_time(cls, time: int) -> list[str]:
        pools = [interval.data for interval in cls.__time_tree[time]]
        pools.sort(key=lambda pool: abs(pool['start'] - time))
        return [pool['id'] for pool in pools]

    @classmethod
    def get_now_pools(cls) -> list[str]:
        return cls.data['process']

    @classmethod
    def get_pool_id_by_info(cls, real_name: str, time: int) -> str | None:
        if ids_by_real_name := cls.pool_name_to_id.get(real_name):
            ids_by_time = set(cls.get_pool_id_by_time(time))
            if intersecting_ids := ids_by_time.intersection(ids_by_real_name):
                return next(iter(intersecting_ids))
        return None

    @staticmethod
    def get_pool_count_type(pool_info: dict[str, str | int | dict[str, int]]) -> str:
        match pool_info['type']:
            case 'LIMITED' | 'LINKAGE' | 'ATTAIN' | 'CLASSIC_ATTAIN':
                return pool_info['name']
            case 'SINGLE' | 'NORMAL' | 'SPECIAL':
                return '标准寻访'
            case 'CLASSIC' | 'FESCLASSIC':
                return '中坚寻访'

    @staticmethod
    def pool_name_fix(real_name: str) -> str:  # 鹰角网络???
        match real_name:
            case '【联合行动】特选干员定向寻访':
                return '联合行动'
            case '进攻-防守-战术交汇':
                return '进攻·防守·战术交汇'
        return real_name


class GiftCodeInfo(JsonData):
    data: dict[str, list[str]] = {
        "OFFICIAL": []
    }
    data_file = 'data/gift_code.json'

    @classmethod
    def get_gift_code(cls, server: str = 'OFFICIAL') -> list[str]:
        return cls.data.get(server, [])


class EmailInfo(JsonData):
    data: dict[str, dict[str, str]] = {
        "verify_email": {
            'subject': '邮箱验证',
            'from': '邮箱验证 <%EMAIL%>',
            'content_file': 'data/email/default.html',
        },
        "change_password": {
            'subject': '密码重置',
            'from': '密码重置 <%EMAIL%>',
            'content_file': 'data/email/default.html',
        }
    }
    data_file = 'data/email.json'

    @classmethod
    def get_email(cls, type: str) -> dict[str, str]:
        return cls.data.get(type, {'subject': '邮件系统', 'content_file': 'data/email/default.html', 'from': '%EMAIL%'})


# init
for subclass in JsonData.__subclasses__():
    subclass.init()
