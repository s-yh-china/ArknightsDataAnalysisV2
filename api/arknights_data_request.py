from urllib.parse import quote

from .models import AccountChannel
from .utils import AsyncRequest


class ArknightsDataRequest:

    def __init__(self, token: str):
        self._token: str = token

    async def get_user_info(self) -> dict:
        pass

    async def get_cards_record(self, last_time: int) -> list:
        pass

    async def get_pay_record(self) -> list:
        pass

    async def get_diamond_record(self, last_time: int) -> list:
        pass

    async def get_gift_record(self) -> list:
        pass

    async def try_get_gift(self, gift_code) -> bool:
        pass


class OfficialArknightsDataRequest(ArknightsDataRequest):
    url_user_info = 'https://as.hypergryph.com/u8/user/info/v1/basic'
    url_cards_record = 'https://ak.hypergryph.com/user/api/inquiry/gacha'
    url_pay_record = 'https://as.hypergryph.com/u8/pay/v1/recent'
    url_diamond_record = 'https://ak.hypergryph.com/user/api/inquiry/diamond'
    url_gift_record = 'https://ak.hypergryph.com/user/api/gift/getExchangeLog'
    url_gift_get = 'https://ak.hypergryph.com/user/api/gift/exchange'

    def __init__(self, token: str):
        super().__init__(token)
        self._channel_id: int = 1
        self._payload: dict = {
            "appId": 1,
            "channelMasterId": 1,
            "channelToken": {
                "token": f"{self._token}"
            }
        }

    async def get_user_info(self) -> dict:
        async with AsyncRequest() as request:
            response: dict | str = await request.post_json(self.url_user_info, self._payload)
            if response == 'ERROR' or not response.get('data'):
                raise ValueError('token error')
            else:
                return response.get('data')

    async def get_cards_record(self, last_time: int) -> list:
        async def get_osr_by_page(request: AsyncRequest, page: int) -> list:
            url_cards_record_page = f'{self.url_cards_record}?page={page}&token={quote(self._token, safe="")}&channelId={self._channel_id}'
            response: dict | str = await request.get(url_cards_record_page)
            if response == 'ERROR' or not response.get('data'):
                raise ValueError('osr getter error')
            else:
                return response.get('data').get('list', [])

        async with AsyncRequest() as request:
            data_list = []
            for page in range(1, 75):
                page_data = await get_osr_by_page(request, page)
                if not await self.add_conditional_data(page_data, data_list, last_time):
                    break
            return data_list

    async def get_pay_record(self) -> list:
        async with AsyncRequest() as request:
            response: dict | str = await request.post_json(self.url_pay_record, self._payload)
            if response == 'ERROR' or not response.get('data'):
                raise ValueError('pay record getter error')
            else:
                return response.get('data')

    async def get_diamond_record(self, last_time: int) -> list:
        async def get_diamond_by_page(request: AsyncRequest, page: int) -> list:
            url_diamond_record_page = f'{self.url_diamond_record}?page={page}&token={quote(self._token, safe="")}&channelId={self._channel_id}'
            response: dict | str = await request.get(url_diamond_record_page)
            if response == 'ERROR' or not response.get('data'):
                raise ValueError('diamond record getter error')
            else:
                return response.get('data').get('list', [])

        async with AsyncRequest() as request:
            data_list = []
            for page in range(1, 75):
                page_data = await get_diamond_by_page(request, page)
                if not await self.add_conditional_data(page_data, data_list, last_time):
                    break
            return data_list

    async def get_gift_record(self) -> list:
        async with AsyncRequest() as request:
            url_gift_record = f'{self.url_gift_record}?token={quote(self._token, safe="")}&channelId={self._channel_id}'
            response: dict | str = await request.get(url_gift_record)
            if response == 'ERROR' or not response.get('data'):
                raise ValueError('gift record getter error')
            else:
                return response.get('data')

    async def try_get_gift(self, gift_code) -> bool:
        async with AsyncRequest() as request:
            payload = {
                'giftCode': f'{gift_code}',
                'token': f'{self._token}',
                'channelId': self._channel_id
            }
            response: dict | str = await request.post_json_with_csrf(self.url_gift_get, payload)
            if response == 'ERROR':
                raise ValueError('gift get error')
            else:
                return response.get('code', 9999) == 200

    @staticmethod
    async def add_conditional_data(page_data: list, data_list: list, last_time: int) -> bool:
        left, right = 0, len(page_data)

        while left < right:
            mid = (left + right) // 2
            mid_time = page_data[mid]['ts']

            if mid_time > last_time:
                right = mid
            else:
                left = mid + 1

        if left < len(page_data):
            data_list.extend(page_data[left:])
            return True
        else:
            return False


class BiliBiliArknightsDataRequest(OfficialArknightsDataRequest):
    def __init__(self, token: str):
        super().__init__(token)
        self._channel_id: int = 2
        self._payload: dict = {
            'token': f'{self._token}'
        }


def create_request_by_token(token: str, channel: AccountChannel) -> ArknightsDataRequest:
    match channel:
        case AccountChannel.BILIBILI:
            return BiliBiliArknightsDataRequest(token)
        case AccountChannel.OFFICIAL:
            return OfficialArknightsDataRequest(token)
