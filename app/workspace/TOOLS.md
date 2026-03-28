# TOOLS.md - 本地笔记

技能定义了工具_如何_工作。这个文件放的是_你的_细节——属于你独特配置的独有信息。

## 网页搜索

需要当前信息时使用网页搜索，例如：

- 实时旅行限制或 advisories
- 开放时间、票价
- 天气预报
- 当地活动
- 最新评价或新闻

## 旅行工具

例如：

- 偏好的预订平台
- 汇率换算参考
- 时区备注
- 当地紧急联系电话
- 翻译贴士

## 示例

```markdown
### 预订偏好

- 机票：优先选择直飞航线
- 酒店：先查看取消政策

### 当地知识

- 城市昵称、发音指南
- 常见旅游骗局需要警告的
- 各国产权习惯

### 紧急情况

- 各地区当地紧急联系电话
- 最近的大使馆联系方式
- 医院推荐标准
```

## 为什么要分开？

技能是共享的。你的配置是你的。分开保存意味着你可以更新技能而不丢失笔记，也可以分享技能而不泄露你的基础设施。

## Memory Tools

### write_memory
Write important information to long-term memory (MEMORY.md).
Parameters: content (string) - what to remember

### append_daily_log
Append entry to today's session log.
Parameters: session_id, human_message, ai_message

### search_memory
Search across all memory files using semantic similarity.
Parameters: query (string), top_k (int, default 5)
Returns: Relevant memory chunks with scores

---

添加任何对你工作有帮助的东西。这是你的参考小抄。
