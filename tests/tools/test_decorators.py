import pytest
import time
from app.tools.decorators import tool_meta, retry, cached


class TestToolMeta:
    def test_tool_meta_sets_name(self):
        @tool_meta(name="custom_name")
        def my_tool(x):
            return x
        assert my_tool.tool_meta.name == "custom_name"

    def test_tool_meta_sets_description(self):
        @tool_meta(description="My description")
        def my_tool(x):
            return x
        assert my_tool.tool_meta.description == "My description"

    def test_tool_meta_sets_tags(self):
        @tool_meta(tags=["tag1", "tag2"])
        def my_tool(x):
            return x
        assert my_tool.tool_meta.tags == ["tag1", "tag2"]

    def test_tool_meta_sets_examples(self):
        examples = [{"input": {"x": "hello"}, "output": "hello"}]
        @tool_meta(examples=examples)
        def my_tool(x):
            return x
        assert my_tool.tool_meta.examples == examples

    def test_tool_meta_defaults(self):
        @tool_meta()
        def my_tool(x):
            return x
        assert my_tool.tool_meta.name == "my_tool"
        assert my_tool.tool_meta.description == ""
        assert my_tool.tool_meta.tags == []
        assert my_tool.tool_meta.examples == []


class TestRetryDecorator:
    def test_retry_on_success(self):
        call_count = 0

        @retry(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure_then_success(self):
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Transient error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_exhausted(self):
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()
        assert call_count == 3

    def test_retry_with_specific_exceptions(self):
        call_count = 0

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def only_value_error():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Not a ValueError")

        with pytest.raises(ConnectionError):
            only_value_error()
        assert call_count == 3  # Should not retry since exception doesn't match


class TestCachedDecorator:
    def test_cached_returns_same_result(self):
        call_count = 0

        @cached(ttl=60)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_func(5)
        result2 = expensive_func(5)
        assert result1 == result2 == 10
        assert call_count == 1  # Second call should use cache

    def test_cached_different_args(self):
        call_count = 0

        @cached(ttl=60)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = func(5)
        result2 = func(10)
        assert result1 == 10
        assert result2 == 20
        assert call_count == 2  # Different args, no cache hit

    def test_cached_max_size_eviction(self):
        call_count = 0

        @cached(ttl=60, max_size=2)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        func(1)
        func(2)
        func(3)  # Should evict oldest entry (1)
        func(1)  # Should recalculate since 1 was evicted
        assert call_count == 4  # All calls were fresh

    def test_cached_no_cache_by_default(self):
        """验证默认不缓存（保守策略）"""
        call_count = 0

        @cached()  # 默认 ttl=0 表示不缓存
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        func(5)
        func(5)
        assert call_count == 2  # No caching when ttl=0
