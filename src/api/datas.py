import os
import json

from typing import override

import httpx

from intervaltree import IntervalTree


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


class ConfigData(JsonData):
    version: str = '0.2.1'
    database_version: str = '0.1.0'
    data: dict = {
        'version': version,
        'database_version': database_version,
        'safe': {
            'SECRET_KEY': os.urandom(32).hex(),
            'ALGORITHM': 'HS256',
            'DEBUG': False,
            'LOG_LEVEL': 'INFO',
            'CORS': {
                'allow_origins': ['*'],
                'allow_credentials': True,
                'allow_methods': ['*'],
                'allow_headers': ['*']
            }
        },
        'user': {
            'email_verify': False,
            'password_reset': False
        },
        'email': {
            'smtp': '',
            'port': 465,
            'username': '',
            'password': '',
            'use_tls': True
        },
        'analysis': {
            'update_time': '20 4 * * *',
            'auto_gift': '0 5 * * *',
            'pool_info_update': '15 4 * * *',
            'pool_info_url': 'https://raw.githubusercontent.com/s-yh-china/ArknightsGachaData/refs/heads/master/data/pool_info.json'
        },
        'mysql': {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': '',
            'port': 3306
        },
        'web': {
            'host': '0.0.0.0',
            'port': 8000,
            'workers': None,
            "forward-ip": []
        }
    }
    data_file = 'config.json'

    @classmethod
    @override
    def init(cls) -> bool:
        if not os.path.exists(cls.data_file):
            cls.update_data()
            print('Need Update Config')
            exit(1)
        else:
            cls.check_version()
            cls.load_data()
        return False

    @classmethod
    def check_version(cls):
        with open(cls.data_file, encoding='utf-8') as json_file:
            local_config = json.load(json_file)
        if local_config.get('version', '0.0.0') != cls.version:
            cls.update_config_version(local_config)

    @classmethod
    def update_config_version(cls, local_config: dict):
        config_version = local_config.get('version', '0.0.0')
        if config_version == '0.0.0':
            local_config = cls.data
        if config_version == '0.1.0' or config_version == '0.1.1':
            config_version = '0.2.0'
            local_config['web'] = {
                'host': '0.0.0.0',
                'port': 8000,
                'workers': None,
                "forward-ip": []
            }
            local_config['database_version'] = '0.1.0'
            local_config['safe']['LOG_LEVEL'] = 'INFO'
        if config_version == '0.2.0':
            config_version = '0.2.1'
            del local_config['email']['link']
        local_config['version'] = config_version
        cls.data = local_config
        cls.update_data()

    @classmethod
    def get_email(cls):
        return cls.data['email']

    @classmethod
    def get_safe(cls):
        return cls.data['safe']

    @classmethod
    def get_mysql(cls):
        return cls.data['mysql']

    @classmethod
    def get_and_update_database_version(cls) -> str:
        database_version = cls.data['database_version']
        if database_version != cls.database_version:
            cls.data['database_version'] = cls.database_version
            cls.update_data()
        return database_version

    @classmethod
    def get_user(cls):
        return cls.data['user']

    @classmethod
    def get_analysis(cls):
        return cls.data['analysis']

    @classmethod
    def get_web(cls):
        return cls.data['web']


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
            cls.data = httpx.get(ConfigData.get_analysis()['pool_info_url']).json()
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
