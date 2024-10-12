import time
import asyncio

from typing import Callable, Any

from aiocache import Cache
from aiocache.serializers import JsonSerializer
from functools import wraps


def cached_with_refresh(ttl: int, key_builder: Callable[[], str]):
    def decorator(func: Callable[[], Any]):
        @wraps(func)
        async def wrapper():
            key = key_builder()
            result, expiry_time = await cache.get(key, (None, None))
            if result is not None:
                if time.time() > expiry_time:
                    _ = asyncio.create_task(cache.set(key, (await func(), time.time() + ttl)))
            else:
                result = await func()
                await cache.set(key, (result, time.time() + ttl))
            return result

        return wrapper

    return decorator


cache = Cache(Cache.MEMORY, serializer=JsonSerializer())
