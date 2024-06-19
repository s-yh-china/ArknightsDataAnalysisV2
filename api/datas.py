import os
import json
import httpx

from intervaltree import IntervalTree


class JsonData:
    __data: dict = {}

    def __init__(self, data_file: str):
        self.data_file: str = data_file
        if not os.path.exists(self.data_file):
            self.update_data()
            self.load_data()
        else:
            self.load_data()

    def load_data(self) -> dict:
        with open(self.data_file, 'r', encoding='utf-8') as json_file:
            type(self).data = json.load(json_file)
        return type(self).__data

    def update_data(self) -> None:
        with open(self.data_file, 'w', encoding='utf-8') as json_file:
            json.dump(type(self).__data, json_file, indent=4, ensure_ascii=False)

    @classmethod
    def get_data(cls) -> dict:
        return cls.__data


class PoolInfo(JsonData):
    __time_tree: IntervalTree
    pool_name_to_id: dict[str, list[str]]

    def __init__(self):
        super().__init__('data/pool_info.json')

    def load_data(self) -> dict:
        super().load_data()
        self.__time_tree = IntervalTree()
        self.pool_name_to_id = {}
        for pool in self.__data['pool'].values():
            self.__time_tree[pool['start']:pool['end'] + 1] = pool
            if pool['real_name'] not in self.pool_name_to_id:
                self.pool_name_to_id[pool['real_name']] = []
            self.pool_name_to_id[pool['real_name']].append(pool['id'])
        return self.__data

    def update_data(self) -> None:
        try:
            type(self).data = httpx.get('').json()  # TODO 加上网址
        except Exception as e:
            print(f'Update PoolInfo Error: {e}')
        super().update_data()

    @classmethod
    def get_all_pools(cls) -> dict[str, dict[str, str | int | dict[str, int] | list[str]]]:
        return cls.__data['pool']

    @classmethod
    def get_pool_info(cls, pool_id: str | None) -> dict[str, str | int | dict[str, int] | list[str]]:
        if pool_id is not None:
            if pool_info := cls.__data['pool'].get(pool_id):
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
        return cls.__data['process']

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
            case 'SINGLE' | 'NORMAL':
                return '标准寻访'
            case 'CLASSIC' | 'FESCLASSIC':
                return '中坚寻访'


class GiftCodeInfo(JsonData):
    __data: dict[str, list[str]] = {
        "OFFICIAL": []
    }

    def __init__(self):
        super().__init__('data/gift_code.json')

    @classmethod
    def get_gift_code(cls, server: str = 'OFFICIAL') -> list[str]:
        return cls.__data.get(server, [])

    def update_data(self) -> None:
        pass


class ConfigData(JsonData):
    __data: dict = {
        'version': '0.1.0',
        'safe': {
            'SECRET_KEY': os.urandom(32).hex(),
            'ALGORITHM': 'HS256',
            'DEBUG': False,
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
            'use_tls': True,
            'link': ''
        },
        'analysis': {
            'update_time': '0 4 * * *',
            'auto_gift': '0 5 * * *'
        },
        'mysql': {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': '',
            'port': 3306
        }
    }

    def __init__(self):
        super().__init__('config.json')

    @classmethod
    def get_email(cls):
        return cls.__data['email']

    @classmethod
    def get_safe(cls):
        return cls.__data['safe']

    @classmethod
    def get_mysql(cls):
        return cls.__data['mysql']

    @classmethod
    def get_user(cls):
        return cls.__data['user']

    def update_data(self) -> None:
        super().update_data()
        print('Need Update Config')
        exit(1)


# init
ConfigData()
PoolInfo()
GiftCodeInfo()
