from typing import cast
from urllib.parse import quote

from typing_extensions import override

from api.models import AccountChannel
from api.utils import AsyncRequest
from abc import ABC, abstractmethod


class ArknightsDataRequest(ABC):

    def __init__(self, token: str):
        self._token: str = token

    @abstractmethod
    async def get_user_info(self) -> dict[str, object]:
        ...

    @abstractmethod
    async def get_cards_record(self, last_time: int) -> list[dict[str, object]]:
        ...

    @abstractmethod
    async def get_pay_record(self) -> list[dict[str, object]]:
        ...

    @abstractmethod
    async def get_diamond_record(self, last_time: int) -> list[dict[str, object]]:
        ...

    @abstractmethod
    async def get_gift_record(self) -> list[dict[str, object]]:
        ...

    @abstractmethod
    async def try_get_gift(self, gift_code: str) -> bool:
        ...


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
        self._payload: dict[str, object] = {
            "appId": 1,
            "channelMasterId": 1,
            "channelToken": {
                "token": f"{self._token}"
            }
        }

    @override
    async def get_user_info(self) -> dict[str, object]:
        async with AsyncRequest() as request:
            try:
                return AsyncRequest.get_response(dict[str, object], await request.post_json(self.url_user_info, self._payload))
            except ValueError:
                raise ValueError('token error')

    @override
    async def get_cards_record(self, last_time: int) -> list[dict[str, object]]:
        async def get_osr_by_page(request: AsyncRequest, page: int) -> list[dict[str, object]]:
            url_cards_record_page = f'{self.url_cards_record}?page={page}&token={quote(self._token, safe="")}&channelId={self._channel_id}'
            try:
                return AsyncRequest.get_response(dict[str, list[dict[str, object]]], await request.get(url_cards_record_page)).get('list', [])
            except ValueError:
                raise ValueError('osr getter error')

        async with AsyncRequest() as request:
            data_list: list[dict[str, object]] = []
            for page in range(1, 75):
                page_data = await get_osr_by_page(request, page)
                if not await self.add_conditional_data(page_data, data_list, last_time):
                    break
            return data_list

    @override
    async def get_pay_record(self) -> list[dict[str, object]]:
        async with AsyncRequest() as request:
            try:
                return AsyncRequest.get_response(list[dict[str, object]], await request.post_json(self.url_pay_record, self._payload))
            except ValueError:
                raise ValueError('pay record getter error')

    @override
    async def get_diamond_record(self, last_time: int) -> list[dict[str, object]]:
        async def get_diamond_by_page(request: AsyncRequest, page: int) -> list[dict[str, object]]:
            url_diamond_record_page = f'{self.url_diamond_record}?page={page}&token={quote(self._token, safe="")}&channelId={self._channel_id}'
            try:
                return AsyncRequest.get_response(dict[str, list[dict[str, object]]], await request.get(url_diamond_record_page)).get('list', [])
            except ValueError:
                raise ValueError('diamond record getter error')

        async with AsyncRequest() as request:
            data_list: list[dict[str, object]] = []
            for page in range(1, 75):
                page_data = await get_diamond_by_page(request, page)
                if not await self.add_conditional_data(page_data, data_list, last_time):
                    break
            return data_list

    @override
    async def get_gift_record(self) -> list[dict[str, object]]:
        async with AsyncRequest() as request:
            url_gift_record = f'{self.url_gift_record}?token={quote(self._token, safe="")}&channelId={self._channel_id}'
            try:
                return AsyncRequest.get_response(list[dict[str, object]], await request.get(url_gift_record))
            except ValueError:
                raise ValueError('gift record getter error')

    @override
    async def try_get_gift(self, gift_code: str) -> bool:
        async with AsyncRequest() as request:
            payload: dict[str, object] = {
                'giftCode': f'{gift_code}',
                'token': f'{self._token}',
                'channelId': self._channel_id
            }
            try:
                response = await request.post_json_with_csrf(self.url_gift_get, payload)
                return cast(int, response.get('code', 9999)) == 200
            except ValueError:
                raise ValueError('gift get error')

    @staticmethod
    async def add_conditional_data(page_data: list[dict[str, object]], data_list: list[dict[str, object]], last_time: int) -> bool:
        left, right = 0, len(page_data)

        while left < right:
            mid = (left + right) // 2
            mid_time: int = cast(int, page_data[mid]['ts'])

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
        self._payload = {
            'token': f'{self._token}'
        }


def create_request_by_token(token: str, channel: AccountChannel) -> ArknightsDataRequest:
    match channel:
        case AccountChannel.BILIBILI:
            return BiliBiliArknightsDataRequest(token)
        case AccountChannel.OFFICIAL:
            return OfficialArknightsDataRequest(token)
