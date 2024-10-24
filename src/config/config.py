import os
import json


class ConfigData:
    version: str = '0.2.2'
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
            "forward_ip": []
        }
    }
    data_file = 'config.json'

    @classmethod
    def init(cls):
        if not os.path.exists(cls.data_file):
            cls.update_data()
            print('Need Update Config')
            exit(1)
        else:
            cls.check_version()
            cls.load_data()

    @classmethod
    def update_data(cls):
        with open(cls.data_file, 'w', encoding='utf-8') as json_file:
            json_file.write(json.dumps(cls.data, indent=4, ensure_ascii=False))

    @classmethod
    def load_data(cls) -> dict:
        with open(cls.data_file, 'r', encoding='utf-8') as json_file:
            cls.data = json.load(json_file)
        return cls.data

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
        if config_version == '0.2.1':
            config_version = '0.2.2'
            local_config['web']['forward_ip'] = local_config['web'].pop('forward-ip')
        local_config['version'] = config_version
        cls.data = local_config
        cls.update_data()

    @classmethod
    def get_and_update_database_version(cls) -> str:
        database_version = cls.data['database_version']
        if database_version != cls.database_version:
            cls.data['database_version'] = cls.database_version
            cls.update_data()
        return database_version
