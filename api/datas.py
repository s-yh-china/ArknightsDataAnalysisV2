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
    data: dict = {
        'gift_codes': {
            'OFFICIAL': ['2023SPECIALCANDY', '00SUMMERCARNIVAL', '02023CELEBRATION', '2024ARKNIGHTSCNY',
                         '0JIACHENLONGNIAN']
        },
        'pool': {
            '常驻标准寻访': {
                'type': '标准寻访',
                'is_up_pool': False
            },
            '中坚寻访': {
                'type': '中坚寻访',
                'is_up_pool': False
            },
            '未知寻访': {
                'type': '未知寻访',
                'is_up_pool': False
            },
            '一线微明': {
                'type': '标准寻访',
                'is_up_pool': True,
                'up_operators': ['莱伊']
            },
            '千秋一粟': {
                'type': '千秋一粟',
                'is_up_pool': True,
                'up_operators': ['黍', '左乐']
            }
        },
        'pool_progress': [
            '常驻标准寻访', '中坚寻访', '千秋一粟'
        ]
    }

    def __init__(self):
        super().__init__('data/analysis.json')


class ConfigData(JsonData):
    data: dict = {
        'safe': {
            'SECRET_KEY': os.urandom(32).hex(),
            'ALGORITHM': 'HS256',
            'DEBUG': False
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
