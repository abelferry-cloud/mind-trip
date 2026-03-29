# Workspace 文件双向同步设计方案

## 背景

前端 `Inspector` 组件（右侧面板）展示 markdown 文件，当前存在问题：
1. 文件列表硬编码在 `files` 数组中
2. `/api/files/${fileName}` 端点**不存在于后端**
3. 保存功能是 mock 的，未真正写入文件
4. `MEMORY.md` 文件位置与 `app/workspace/` 不一致

用户期望：
- 文件地址使用 `app/workspace/` 下的真实文件
- 前端修改能同步到后端（保存）
- 后端修改能同步到前端（轮询检测）

## 架构设计

### 1. 后端：新增 `/api/workspace/` 路由

新建文件 `app/api/workspace.py`：

```python
router = APIRouter(prefix="/api/workspace", tags=["workspace"])
WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"

class FileInfo(BaseModel):
    name: str
    path: str
    modified_at: datetime

class FileContent(BaseModel):
    name: str
    content: str
    modified_at: datetime

@router.get("/files", response_model=List[FileInfo])
async def list_workspace_files():
    """返回 workspace 目录下所有 md 文件"""

@router.get("/files/{filename}", response_model=FileContent)
async def get_workspace_file(filename: str):
    """读取指定文件内容"""

@router.put("/files/{filename}")
async def save_workspace_file(filename: str, body: FileContent):
    """保存文件内容"""
```

### 2. 前端：Inspector 组件改造

**文件列表获取**
- 移除硬编码的 `files` 数组
- 组件挂载时 GET `/api/workspace/files` 动态加载文件列表

**内容加载**
- 切换文件时 GET `/api/workspace/files/{filename}`
- 每 3 秒轮询文件修改时间，若变化则自动刷新内容

**保存功能**
- 点击"保存"按钮时 PUT `/api/workspace/files/{filename}` + `{ content }`
- 保存成功后清除 `isModified` 状态

**MEMORY.md 单独处理**
- `MEMORY.md` 位于 `app/memory/MEMORY.md`，不纳入 workspace 文件列表
- Inspector 中如需展示 MEMORY.md，维持原有逻辑

### 3. 同步机制

| 方向 | 触发 | 实现 |
|------|------|------|
| 前端 → 后端 | 用户点击"保存" | PUT `/api/workspace/files/{filename}` |
| 后端 → 前端 | 轮询检测（每 3 秒） | GET `/api/workspace/files` 比对 `modified_at` |

### 4. 文件位置

```
app/workspace/          ← Inspector 编辑的文件
├── SOUL.md
├── IDENTITY.md
├── USER.md
├── AGENTS.md
├── TOOLS.md
├── SYSTEM_PROMPT_budget.md
├── SYSTEM_PROMPT_preference.md
├── SYSTEM_PROMPT_supervisor.md
└── BOOTSTRAP.md

app/memory/
└── MEMORY.md           ← 长期记忆（不纳入 workspace）
```

## 实现步骤

### Step 1: 后端 API
- [ ] 新建 `app/api/workspace.py`
- [ ] 实现 `GET /api/workspace/files` 列出文件
- [ ] 实现 `GET /api/workspace/files/{filename}` 读取内容
- [ ] 实现 `PUT /api/workspace/files/{filename}` 保存内容
- [ ] 在 `app/main.py` 注册路由

### Step 2: 前端 Inspector 改造
- [ ] 移除硬编码文件列表
- [ ] 动态加载文件列表（GET `/api/workspace/files`）
- [ ] 实现文件加载（GET `/api/workspace/files/{filename}`）
- [ ] 实现文件保存（PUT `/api/workspace/files/{filename}`）
- [ ] 添加轮询机制（每 3 秒检查修改时间）

## 约束

- 单用户场景，暂不处理并发编辑冲突
- 轮询间隔 3 秒（可配置）
- 仅支持 `app/workspace/` 目录下的 `.md` 文件
