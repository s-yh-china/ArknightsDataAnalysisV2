import os
import json


class JsonData:
    data: dict = {}

    def __init__(self, data_file: str):
        self.data_file: str = data_file
        if not os.path.exists(self.data_file):
            self.update_data()
        else:
            self.load_data()

    def load_data(self) -> dict:
        with open(self.data_file, 'r', encoding='utf-8') as json_file:
            self.data = json.load(json_file)
        return self.data

    def update_data(self) -> None:
        with open(self.data_file, 'w', encoding='utf-8') as json_file:
            json.dump(self.data, json_file, indent=4, ensure_ascii=False)

    def get_data(self) -> dict:
        return self.data


class AnalysisData(JsonData):
    def update_data(self) -> None:
        pass

    def __init__(self):
        super().__init__('data/analysis.json')


class ConfigData(JsonData):
    data: dict = {
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

    def update_data(self) -> None:
        super().update_data()
        print('Need Update Config')
        exit(1)
