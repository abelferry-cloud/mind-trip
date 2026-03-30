import pytest
from app.tools.registry import ToolRegistry, tool_registry


class TestToolRegistry:
    def test_singleton_pattern(self):
        """验证单例模式"""
        r1 = ToolRegistry()
        r2 = ToolRegistry()
        assert r1 is r2

    def test_global_registry_instance(self):
        """验证全局实例"""
        assert tool_registry is not None
        assert isinstance(tool_registry, ToolRegistry)

    def test_register_and_get_tool(self):
        """测试工具注册和获取"""
        registry = ToolRegistry()
        test_tool = lambda x: x

        registry.register(test_tool, name="test_tool")
        retrieved = registry.get_tool("test_tool")
        assert retrieved is test_tool

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具"""
        registry = ToolRegistry()
        result = registry.get_tool("nonexistent")
        assert result is None

    def test_list_tools(self):
        """测试列出所有工具"""
        registry = ToolRegistry()
        registry.register(lambda: None, name="tool1", tags=["tag1"])
        registry.register(lambda: None, name="tool2", tags=["tag2"])

        tools = registry.list_tools()
        assert len(tools) >= 2
        tool_names = [t["name"] for t in tools]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    def test_list_tools_by_tags(self):
        """测试按标签筛选工具"""
        registry = ToolRegistry()
        registry.register(lambda: None, name="travel_tool", tags=["travel", "search"])
        registry.register(lambda: None, name="budget_tool", tags=["budget"])

        travel_tools = registry.list_tools(tags=["travel"])
        assert len(travel_tools) >= 1
        assert travel_tools[0]["name"] == "travel_tool"

    def test_get_tool_schemas(self):
        """测试获取工具 schema"""
        registry = ToolRegistry()

        def sample_tool(city: str, page_size: int = 10):
            return [{"city": city, "count": page_size}]

        registry.register(
            sample_tool,
            name="sample_tool",
            description="Sample tool for testing",
            tags=["test"]
        )

        schemas = registry.get_tool_schemas()
        assert len(schemas) >= 1
        schema_names = [s["name"] for s in schemas]
        assert "sample_tool" in schema_names

    def test_register_with_metadata(self):
        """测试带元数据的注册"""
        registry = ToolRegistry()

        def my_tool(x: str) -> str:
            return x

        registry.register(
            my_tool,
            name="my_tool",
            description="My test tool",
            tags=["test", "sample"],
            examples=[{"input": {"x": "hello"}, "output": "hello"}]
        )

        retrieved = registry.get_tool("my_tool")
        assert retrieved is my_tool
        info = registry.get_tool_info("my_tool")
        assert info["description"] == "My test tool"
        assert info["tags"] == ["test", "sample"]
        assert info["examples"] == [{"input": {"x": "hello"}, "output": "hello"}]

    def test_get_tool_info(self):
        """测试获取工具信息"""
        registry = ToolRegistry()
        registry.register(lambda: None, name="info_tool", description="Info tool")
        info = registry.get_tool_info("info_tool")
        assert info is not None
        assert info["name"] == "info_tool"
        assert info["description"] == "Info tool"

    def test_get_info_nonexistent(self):
        """测试获取不存在工具的信息"""
        registry = ToolRegistry()
        info = registry.get_tool_info("nonexistent")
        assert info is None
