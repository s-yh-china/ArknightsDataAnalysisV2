from aiocache import Cache
from aiocache.serializers import JsonSerializer
from functools import wraps
import asyncio
import time


def cached_with_refresh(ttl, key_builder):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_builder(*args, **kwargs)
            result, expiry_time = await cache.get(key, (None, None))

            if result is not None:
                if time.time() > expiry_time:
                    task = asyncio.create_task(cache.set(key, (await func(*args, **kwargs), time.time() + ttl)))
            else:
                result = await func(*args, **kwargs)
                await cache.set(key, (result, time.time() + ttl))

            return result

        return wrapper

    return decorator


cache = Cache(Cache.MEMORY, serializer=JsonSerializer())
