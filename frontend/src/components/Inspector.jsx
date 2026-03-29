import React, { useState, useEffect } from 'react'
import Editor from '@monaco-editor/react'

const Inspector = ({ file, onFileChange, style }) => {
  const [content, setContent] = useState('')
  const [isModified, setIsModified] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const files = [
    { id: 'SOUL.md', path: '/workspace/SOUL.md' },
    { id: 'IDENTITY.md', path: '/workspace/IDENTITY.md' },
    { id: 'USER.md', path: '/workspace/USER.md' },
    { id: 'AGENTS.md', path: '/workspace/AGENTS.md' },
    { id: 'MEMORY.md', path: '/workspace/MEMORY.md' },
    { id: 'TOOLS.md', path: '/workspace/TOOLS.md' },
  ]

  useEffect(() => {
    // Load file content when file changes
    loadFileContent(file)
  }, [file])

  const loadFileContent = async (fileName) => {
    try {
      // Try to fetch from the API or use mock content
      const response = await fetch(`/api/files/${fileName}`)
      if (response.ok) {
        const data = await response.json()
        setContent(data.content)
      } else {
        // Use mock content for demonstration
        setContent(getMockContent(fileName))
      }
      setIsModified(false)
    } catch (error) {
      setContent(getMockContent(fileName))
      setIsModified(false)
    }
  }

  const getMockContent = (fileName) => {
    const contents = {
      'SOUL.md': `# SOUL.md - 核心灵魂

## 使命宣言
SmartJourney 是一个智能旅行规划助手，旨在为用户提供个性化、高效、深度体验式的旅行规划服务。

## 核心原则
1. **用户至上** - 始终以用户需求为出发点
2. **数据驱动** - 基于用户偏好和历史数据提供精准推荐
3. **持续学习** - 通过每次交互不断优化个性化服务
4. **透明可解释** - 让用户理解推荐背后的逻辑

## 沟通风格
- 专业但亲切，避免过度技术化术语
- 主动提问以深入了解用户需求
- 提供多方案选择而非单一答案
- 适度使用 emoji 增添趣味性

## 响应规范
- 响应时间应简洁有力
- 复杂问题分步骤解答
- 不确定时坦诚告知用户`,
      'MEMORY.md': `# MEMORY.md - 记忆系统

## 当前会话记忆
- 用户正在规划：重庆三日游
- 预算范围：2000-3000元
- 出行人数：2人
- 偏好标签：美食、摄影、小众景点

## 长期偏好
- 住宿：倾向于有特色的民宿
- 餐饮：喜欢当地特色小吃
- 交通：prefer公共交通
- 节奏：不喜欢赶路，注重深度体验

## 历史交互
- 2026-03-25: 规划了杭州周末美食之旅
- 2026-03-20: 咨询了云南旅行注意事项`,
      'IDENTITY.md': `# IDENTITY.md - 身份定义

## 角色名称
SmartJourney 智能旅行规划助手

## 角色定位
- 专业的旅行规划顾问
- 细心的偏好记忆管家
- 贴心的行程管家

## 能力边界
- 擅长：行程规划、预算分配、偏好匹配
- 有限支持：实时交通、天气查询
- 暂不支持：实际预订、支付功能`,
      'USER.md': `# USER.md - 用户上下文

## 当前用户
- 用户ID: default_user
- 会员等级: 普通会员
- 信任评分: 85/100

## 当前会话
- 会话ID: ${Date.now()}
- 开始时间: ${new Date().toLocaleString('zh-CN')}
- 消息数: 0`,
      'AGENTS.md': `# AGENTS.md - 多智能体协作

## 架构设计
采用星型拓扑结构，PlanningAgent 作为中枢协调各专业智能体。

## 智能体职责
1. **PlanningAgent**: 意图解析、任务分发、结果整合
2. **AttractionsAgent**: 景点推荐、开放时间、门票信息
3. **RouteAgent**: 路线规划、时间优化、地理匹配
4. **BudgetAgent**: 预算分配、成本控制、超支预警
5. **FoodAgent**: 美食推荐、餐厅预约信息
6. **HotelAgent**: 住宿推荐、位置匹配、设施评估
7. **PreferenceAgent**: 偏好学习、记忆更新

## 协作流程
并行 -> 串行 -> 并行的混合模式`,
      'TOOLS.md': `# TOOLS.md - 工具配置

## 可用工具
1. **search_attractions**: 搜索景点信息
2. **search_restaurants**: 搜索餐厅信息
3. **search_hotels**: 搜索酒店信息
4. **calculate_route**: 计算路线距离
5. **estimate_budget**: 预算估算
6. **query_memory**: 查询记忆数据

## 工具调用策略
- 简单查询：单一工具
- 复杂任务：多工具并行
- 关键决策：工具 + 人工确认`
    }
    return contents[fileName] || '# 文件内容加载中...'
  }

  const handleEditorChange = (value) => {
    setContent(value)
    setIsModified(true)
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // In real implementation, this would save to the backend
      await new Promise(resolve => setTimeout(resolve, 500))
      setIsModified(false)
    } catch (error) {
      console.error('Failed to save:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const currentFile = files.find(f => f.id === file)

  return (
    <aside className="inspector" style={style}>
      <div className="inspector-header">
        <div className="inspector-title">
          <CodeIcon />
          <span>Inspector</span>
        </div>
      </div>

      <div className="inspector-tabs">
        {files.map(f => (
          <button
            key={f.id}
            className={`inspector-tab ${file === f.id ? 'active' : ''}`}
            onClick={() => onFileChange(f.id)}
          >
            {f.id}
          </button>
        ))}
      </div>

      <div className="inspector-content">
        <Editor
          height="100%"
          language="markdown"
          theme="vs"
          value={content}
          onChange={handleEditorChange}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: 'JetBrains Mono, Fira Code, monospace',
            lineNumbers: 'on',
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 12 },
            renderLineHighlight: 'line',
            cursorBlinking: 'smooth',
            smoothScrolling: true,
          }}
        />
      </div>

      <div className="inspector-footer">
        <div className="inspector-status">
          {isModified ? (
            <>
              <DotIcon style={{ color: 'var(--warning)' }} />
              <span>已修改</span>
            </>
          ) : (
            <>
              <DotIcon style={{ color: 'var(--success)' }} />
              <span>已同步</span>
            </>
          )}
        </div>
        <button
          className="stage-action-btn"
          onClick={handleSave}
          disabled={!isModified || isSaving}
          style={{ opacity: isModified ? 1 : 0.5 }}
        >
          {isSaving ? '保存中...' : '保存'}
        </button>
      </div>
    </aside>
  )
}

const CodeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 18 22 12 16 6" />
    <polyline points="8 6 2 12 8 18" />
  </svg>
)

const DotIcon = ({ style }) => (
  <span style={{ ...style, width: 6, height: 6, borderRadius: '50%', display: 'inline-block' }} />
)

export default Inspector
