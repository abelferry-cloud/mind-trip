# LangChain Tool 高级功能设计

**日期**: 2026-03-30
**状态**: Approved
**负责人**: Claude

---

## 1. 背景与目标

### 现状
`app/tools/` 目录下有 3 个工具文件：
- `travel_skills.py` — 6 个工具，依赖高德地图（Amap）+ Tavily 外部 API
- `budget_tools.py` — 2 个异步函数，无外部依赖
- `context_tools.py` — 4 个工具，操作 workspace 文件

当前工具使用 `@tool` 装饰器但无显式名称、参数校验、错误处理或重试机制。

### 目标
基于 LangChain 官方 API（`@tool`、`StructuredTool.from_function`），为工具添加：
1. **显式元数据** — 自定义 name、description、tags
2. **参数校验** — Pydantic `args_schema`
3. **结构化错误处理** — typed error classes + retry
4. **可观测性** — 追踪信息

---

## 2. LangChain Tool API 参考

### 2.1 `@tool` 装饰器（官方）
```python
from langchain_core.tools import tool
from langchain.pydantic_v1 import BaseModel, Field

@tool("custom_name", return_direct=False, tags=["travel"])
def my_tool(arg1: str, arg2: int = 5) -> str:
    """Description used by LLM to decide when to call this tool."""
    ...

# args_schema 支持 Pydantic BaseModel
class MyInput(BaseModel):
    arg1: str = Field(description="...")
    arg2: int = Field(default=5, description="...")

@tool("custom_name", args_schema=MyInput)
def my_tool(arg1: str, arg2: int = 5) -> str:
    ...
```

### 2.2 `StructuredTool.from_function`（官方）
```python
from langchain_core.tools import StructuredTool

StructuredTool.from_function(
    func=my_func,
    name="custom_name",
    description="...",
    args_schema=MyInput,
    tags=["travel"],
    handle_tool_error=True,  # LangChain 原生错误处理
)
```

### 2.3 错误处理（官方）
LangChain 原生支持 `handle_tool_error` 参数，也支持自定义 `BaseTool` 子类实现 `invoke` 方法中的 try/except。

### 2.4 异步支持（官方）
`@tool` 装饰器自动支持 async 函数：
```python
@tool
async def async_search(query: str) -> dict:
    ...
```

---

## 3. 文件结构

```
app/tools/
├── __init__.py              # 导出所有工具
├── errors.py                # 新建：结构化错误类
├── retry_decorator.py       # 新建：重试装饰器（基于 tenacity）
├── travel_skills.py         # 改进：+ args_schema, 显式 name/description, retry, error handling
└── context_tools.py         # 改进：+ args_schema, 显式 name, error handling
```

`budget_tools.py` 保持不变（无外部 API 依赖，无需重试/错误处理）。

---

## 4. 详细设计

### 4.1 `errors.py` — 结构化错误类

基于 LangChain 错误处理最佳实践，自定义异常继承自 `ToolExecutionError`：

```python
# app/tools/errors.py
from typing import Optional
from langchain_core.tools import ToolExecutionError

class BaseAPIError(ToolExecutionError):
    """外部 API 调用失败的基类。"""
    def __init__(self, tool_name: str, message: str, cause: Optional[Exception] = None):
        self.tool_name = tool_name
        self.cause = cause
        super().__init__(f"[{tool_name}] {message}")

class RateLimitError(BaseAPIError):
    """API 速率限制错误（高德/ Tavily 通用）。"""
    pass

class APIResponseError(BaseAPIError):
    """API 返回异常数据（状态码非 200 或响应体异常）。"""
    pass

class APITimeoutError(BaseAPIError):
    """API 请求超时。"""
    pass

class APIKeyMissingError(BaseAPIError):
    """缺少必需的 API Key。"""
    pass

class ValidationError(ToolExecutionError):
    """输入参数校验失败。"""
    pass

class FileOperationError(ToolExecutionError):
    """workspace 文件操作失败。"""
    pass
```

### 4.2 `retry_decorator.py` — 重试装饰器

基于 `tenacity` 实现指数退避重试，专用于高德/Tavily 等不稳定外部 API：

```python
# app/tools/retry_decorator.py
import functools
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.tools.errors import RateLimitError, APITimeoutError

logger = structlog.get_logger()

def with_retry(max_attempts: int = 3, tool_name: str = "unknown"):
    """指数退避重试装饰器。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)  # 同步版本由具体工具调用时包装

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except RateLimitError:
                logger.warning(f"[{tool_name}] rate limited, retrying...")
                raise  # 让 tenacity 处理
            except APITimeoutError:
                logger.warning(f"[{tool_name}] timed out, retrying...")
                raise
            except Exception as e:
                logger.error(f"[{tool_name}] unexpected error: {e}")
                raise

        return async_wrapper if functools.iscoroutinefunction(func) else wrapper
    return decorator
```

> **注意**：实际重试逻辑在工具内部通过 `tenacity` 直接使用，不在此装饰器中包装（方便单独控制重试参数）。

### 4.3 `travel_skills.py` — 工具增强

#### 4.3.1 Pydantic 输入 Schema

每个工具的输入参数提取为独立的 Pydantic `BaseModel`：

```python
# --- Pydantic Schemas ---
class SearchAttractionsInput(BaseModel):
    city: str = Field(description="城市名称（中文），例如 '杭州'")

class SearchRestaurantsInput(BaseModel):
    city: str = Field(description="城市名称（中文）")
    cuisine: str = Field(default="", description="菜系类型（可选），例如 '川菜'")

class SearchHotelsInput(BaseModel):
    city: str = Field(description="城市名称（中文）")
    budget: float = Field(default=500.0, description="每晚预算上限（单位：CNY）")
    location: str = Field(default="", description="位置偏好关键词（可选），例如 '西湖区'")

class PlanDrivingRouteInput(BaseModel):
    origin: str = Field(description="起点地址或坐标")
    destination: str = Field(description="终点地址或坐标")
    city: str = Field(default="", description="城市名称（用于地理编码）")

class PlanWalkingRouteInput(BaseModel):
    origin: str = Field(description="起点地址或坐标")
    destination: str = Field(description="终点地址或坐标")
    city: str = Field(default="", description="城市名称")

class TavilySearchInput(BaseModel):
    query: str = Field(description="搜索查询词")
    max_results: int = Field(default=5, description="最大结果数", ge=1, le=10)
```

#### 4.3.2 显式工具定义

```python
@tool(
    "search_attractions",
    args_schema=SearchAttractionsInput,
    description="搜索城市内的景点和博物馆信息。返回景点名称、地址、类型、经纬度坐标，以及根据名称推断的体力消耗强度（high/medium/low）。用于规划旅行行程中的游览安排。",
    tags=["travel", "attractions", "amap"],
)
def search_attractions(city: Annotated[str, "城市名称"]) -> Annotated[List[dict], "景点列表"]:
    """搜索城市景点（风景名胜 + 博物馆）"""
    try:
        mgr = get_map_manager()
        result = mgr.search_attractions(city, page_size=20)
        pois = result.get("pois", [])
        return [...]
    except RateLimitError:
        raise
    except APITimeoutError:
        raise
    except Exception as e:
        raise APIResponseError(tool_name="search_attractions", message=f"高德地图返回异常: {e}", cause=e)
```

#### 4.3.3 重试逻辑

在调用外部 API 的函数层面使用 `tenacity`：

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    reraise=True,
)
async def _search_attractions_with_retry(city: str) -> dict:
    mgr = get_map_manager()
    return mgr.search_attractions(city, page_size=20)
```

### 4.4 `context_tools.py` — 工具增强

#### 4.4.1 改进错误处理

已有的路径安全校验保持不变，添加结构化错误映射：

```python
@tool(
    "update_user_context",
    args_schema=UpdateUserContextInput,
    description="更新用户上下文信息到 USER.md 文件。当用户提供了身份信息（名字、职业、语言偏好等）时调用。静默执行，不在回复中提及。",
    tags=["context", "workspace"],
)
def update_user_context(...) -> Annotated[dict, "更新结果"]:
    try:
        ...
    except FileOperationError:
        raise
    except Exception as e:
        raise FileOperationError(tool_name="update_user_context", message=f"写入失败: {e}", cause=e)
```

### 4.5 `__init__.py` — 统一导出

```python
# app/tools/__init__.py
from app.tools.errors import (
    BaseAPIError,
    RateLimitError,
    APIResponseError,
    APITimeoutError,
    APIKeyMissingError,
    ValidationError,
    FileOperationError,
)

from app.tools.travel_skills import (
    search_attractions,
    search_restaurants,
    search_hotels,
    plan_driving_route,
    plan_walking_route,
    tavily_web_search,
)

from app.tools.context_tools import (
    update_user_context,
    update_agent_identity,
    update_agent_soul,
    read_workspace_file,
)

__all__ = [
    # errors
    "BaseAPIError",
    "RateLimitError",
    "APIResponseError",
    "APITimeoutError",
    "APIKeyMissingError",
    "ValidationError",
    "FileOperationError",
    # travel
    "search_attractions",
    "search_restaurants",
    "search_hotels",
    "plan_driving_route",
    "plan_walking_route",
    "tavily_web_search",
    # context
    "update_user_context",
    "update_agent_identity",
    "update_agent_soul",
    "read_workspace_file",
]
```

---

## 5. 各工具变更清单

| 文件 | 工具 | 变更内容 |
|------|------|---------|
| `errors.py` | 新建 | 7 个错误类 |
| `retry_decorator.py` | 新建 | 重试工具函数 |
| `travel_skills.py` | `search_attractions` | + Pydantic schema、显式 name/description/tags、try/except、retry |
| `travel_skills.py` | `search_restaurants` | 同上 |
| `travel_skills.py` | `search_hotels` | 同上 + budget 范围校验 |
| `travel_skills.py` | `plan_driving_route` | 同上 |
| `travel_skills.py` | `plan_walking_route` | 同上 |
| `travel_skills.py` | `tavily_web_search` | 同上 + API key 缺失检测 |
| `context_tools.py` | `update_user_context` | + Pydantic schema、显式 name/tags、try/except |
| `context_tools.py` | `update_agent_identity` | 同上 |
| `context_tools.py` | `update_agent_soul` | 同上 |
| `context_tools.py` | `read_workspace_file` | 同上 |
| `__init__.py` | 更新 | 统一导出所有工具和错误类 |

---

## 6. 依赖变更

新增 `tenacity` 依赖：

```bash
pip install tenacity
```

`tenacity` 已在 `requirements.txt` 中或需新增。

---

## 7. 测试策略

1. **单元测试**：为每个 Pydantic schema 编写参数校验测试
2. **错误处理测试**：用 `pytest.raises` 验证各类错误是否正确抛出
3. **Mock 测试**：mock 高德/Tavily API，验证重试逻辑是否触发
4. **集成测试**：确保工具导出后能被 Supervisor 正常加载和使用
