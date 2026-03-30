# LangChain 工具高级功能优化设计

**日期：** 2026-03-30
**状态：** 已批准
**版本：** 1.0

## 1. 背景与目标

当前项目中的工具（位于 `app/tools/`）使用 LangChain `@tool` 装饰器定义，功能正常但缺乏：
- 标准化错误处理
- 参数验证
- 工具元数据
- 重试机制
- 缓存机制
- 统一返回格式

**优化目标：**
- A - 标准化错误处理
- B - 参数验证增强
- C - 工具元数据增强
- D - 重试与超时机制
- E - 缓存机制
- F - 统一返回格式

## 2. 架构决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 改造方式 | 渐进式改造 | 风险可控，不影响现有功能 |
| 工具注册 | 混合模式（装饰器 + Registry） | 灵活性与一致性兼顾 |
| 错误处理 | 增强模式（ToolException + 错误分类） | 便于 Agent 根据错误类型处理 |
| 缓存策略 | 保守策略（opt-in） | 明确性优于隐式行为 |
| 参数验证 | 混合模式（Annotated + Pydantic） | 简单参数保持简洁，复杂参数用 Pydantic |

## 3. 新增文件清单

```
app/tools/
├── base.py              # ToolException、ToolErrorCategory、ToolResult
├── registry.py          # ToolRegistry 工具注册中心（单例）
├── decorators.py       # @tool_meta、@retry、@cached 装饰器
├── travel_skills.py     # 【改造】添加错误处理、重试、缓存
├── budget_tools.py       # 【改造】转换为标准 Tool + Pydantic schema
└── context_tools.py     # 【改造】添加 Pydantic schema
```

## 4. 核心组件设计

### 4.1 异常类 (base.py)

```python
class ToolErrorCategory(Enum):
    API_ERROR = "API_ERROR"           # 外部 API 错误
    VALIDATION_ERROR = "VALIDATION_ERROR"  # 参数验证错误
    NETWORK_ERROR = "NETWORK_ERROR"   # 网络连接错误
    TIMEOUT_ERROR = "TIMEOUT_ERROR"   # 请求超时
    UNKNOWN_ERROR = "UNKNOWN_ERROR"    # 未知错误

class ToolException(Exception):
    def __init__(
        self,
        category: ToolErrorCategory,
        message: str,
        details: dict = None,
        retryable: bool = False
    ):
        self.category = category
        self.message = message
        self.details = details or {}
        self.retryable = retryable  # 是否可重试
```

### 4.2 标准返回格式 (base.py)

```python
@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: ToolException = None
    metadata: dict = field(default_factory=dict)
    # metadata 包含：
    #   - tool_name: str
    #   - duration_ms: int
    #   - cached: bool
    #   - retry_count: int
```

### 4.3 工具注册中心 (registry.py)

```python
class ToolRegistry:
    """单例模式，工具注册中心"""

    def register(
        self,
        tool: Callable,
        name: str = None,
        description: str = None,
        tags: list = None,
        examples: list = None
    ): ...

    def get_tool(self, name: str) -> BaseTool: ...

    def list_tools(self, tags: list = None) -> list: ...

    def get_tool_schemas(self) -> list: ...
```

### 4.4 装饰器 (decorators.py)

#### @tool_meta
```python
@tool_meta(
    name="search_attractions",
    tags=["travel", "search"],
    description="搜索城市景点（风景名胜 + 博物馆）",
    examples=[{"input": {"city": "北京"}, "output": [...]}]
)
```

#### @retry
```python
@retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(NetworkError, TimeoutError))
```
- `max_attempts`: 最大重试次数
- `delay`: 初始延迟（秒）
- `backoff`: 退避倍数
- `exceptions`: 可重试的异常类型

#### @cached
```python
@cached(ttl=3600, max_size=100)  # TTL=1小时，最大100条
```
- `ttl`: 缓存有效期（秒）
- `max_size`: LRU 缓存最大条目数
- **注意：** 默认不缓存（保守策略），工具需要时主动声明

## 5. 工具改造规范

### 5.1 travel_skills.py

| 工具 | 缓存策略 | 重试 | 错误分类 |
|------|----------|------|----------|
| `search_attractions` | 5分钟 TTL | 3次 | API_ERROR, NETWORK_ERROR |
| `search_restaurants` | 5分钟 TTL | 3次 | API_ERROR, NETWORK_ERROR |
| `search_hotels` | 5分钟 TTL | 3次 | API_ERROR, NETWORK_ERROR |
| `plan_driving_route` | 不缓存 | 2次 | API_ERROR, TIMEOUT_ERROR |
| `plan_walking_route` | 不缓存 | 2次 | API_ERROR, TIMEOUT_ERROR |
| `tavily_web_search` | 15分钟 TTL | 3次 | API_ERROR, NETWORK_ERROR |

### 5.2 budget_tools.py

转换为标准 LangChain Tool 格式，添加 Pydantic schema：

```python
class BudgetCalculateInput(BaseModel):
    duration: int = Field(ge=1, le=30, description="旅行天数")
    style: str = Field(description='预算风格: "节省" | "适中" | "奢侈"')

class BudgetCheckInput(BaseModel):
    budget: float = Field(ge=0, description="总预算")
    plan: dict = Field(description="旅行方案")
```

### 5.3 context_tools.py

添加 Pydantic schema 验证：

```python
class UpdateUserContextInput(BaseModel):
    user_name: str = Field(min_length=1, max_length=50)
    preferred_name: str = Field(default="", max_length=50)
    identity: str = Field(default="", max_length=200)
    language: str = Field(default="中文")
    timezone: str = Field(default="Asia/Shanghai")
    notes: str = Field(default="")
```

## 6. 错误处理流程

```
工具执行
    ↓
捕获异常
    ↓
分类为 ToolErrorCategory
    ↓
判断是否可重试 (retryable)
    ↓
返回 ToolResult {
    success: False,
    error: ToolException(...),
    metadata: {retry_count, duration_ms, ...}
}
    ↓
Agent 根据 error.category 决定下一步：
    - VALIDATION_ERROR → 修正参数重试
    - NETWORK_ERROR → 等待后重试
    - API_ERROR → 检查 API 配额或切换方案
    - TIMEOUT_ERROR → 增加超时时间重试
```

## 7. 实现优先级

| 优先级 | 文件/任务 | 说明 |
|--------|-----------|------|
| P0 | `base.py` | 基础设施先行 |
| P0 | `registry.py` | 工具注册中心 |
| P1 | `decorators.py` | 装饰器定义 |
| P1 | `travel_skills.py` 改造 | 添加错误处理、重试 |
| P2 | `budget_tools.py` 改造 | 转换为标准 Tool |
| P3 | `context_tools.py` 改造 | 添加 Pydantic schema |
| P4 | `__init__.py` 更新 | 统一导出 |

## 8. 向后兼容性

- 所有改造保持现有函数签名不变
- 内部实现添加包装层，不改变业务逻辑
- 新旧工具可共存，逐步迁移
- 不引入新的外部依赖
