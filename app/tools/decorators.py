# app/tools/decorators.py
"""工具装饰器：@tool_meta、@retry、@cached"""
import functools
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional, TypeVar, ParamSpec
from dataclasses import dataclass

T = TypeVar("T")
P = ParamSpec("P")


@dataclass
class ToolMeta:
    """工具元数据"""
    name: str = ""
    description: str = ""
    tags: Optional[list] = None
    examples: Optional[list] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.examples is None:
            self.examples = []


def tool_meta(
    name: str = None,
    description: str = None,
    tags: Optional[list] = None,
    examples: Optional[list] = None
):
    """工具元数据装饰器"""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        meta = ToolMeta(
            name=name or func.__name__,
            description=description or "",
            tags=tags or [],
            examples=examples or []
        )
        func.tool_meta = meta  # type: ignore
        return func
    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """重试装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
        exceptions: 可重试的异常类型元组
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 边界检查：max_attempts <= 0 时直接调用原函数
            if max_attempts <= 0:
                return func(*args, **kwargs)

            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        break
                    time.sleep(current_delay)
                    current_delay *= backoff

            raise last_exception

        wrapper.retry_config = {  # type: ignore
            "max_attempts": max_attempts,
            "delay": delay,
            "backoff": backoff,
            "exceptions": exceptions,
        }
        return wrapper
    return decorator


def cached(ttl: int = 0, max_size: int = 100):
    """缓存装饰器（LRU 策略）

    注意：默认不缓存（ttl=0），需要主动声明才启用。

    Args:
        ttl: 缓存有效期（秒），0 表示不缓存
        max_size: LRU 缓存最大条目数
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if ttl <= 0:
            # 不缓存模式
            return func

        cache: OrderedDict = OrderedDict()
        cache_times: OrderedDict = OrderedDict()
        cache_lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 创建可哈希的缓存键
            key = (args, tuple(sorted(kwargs.items())))

            with cache_lock:
                # 检查缓存是否存在且未过期
                if key in cache:
                    cached_time = cache_times.get(key, 0)
                    if time.time() - cached_time < ttl:
                        # 移动到末尾（LRU）
                        cache.move_to_end(key)
                        return cache[key]

                # 执行函数
                result = func(*args, **kwargs)

                # 添加到缓存
                if len(cache) >= max_size:
                    # 移除最老的条目
                    oldest_key = next(iter(cache))
                    del cache[oldest_key]
                    cache_times.pop(oldest_key, None)

                cache[key] = result
                cache_times[key] = time.time()

                return result

        wrapper.cache_info = lambda: {"size": len(cache), "max_size": max_size, "ttl": ttl}  # type: ignore
        wrapper.clear_cache = lambda: (cache.clear(), cache_times.clear())  # type: ignore
        return wrapper
    return decorator


class ToolRetryable(Exception):
    """标记为可重试的工具异常"""
    pass
