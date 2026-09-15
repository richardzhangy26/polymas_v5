# 意图覆盖检查

> 本文件仅定义覆盖分析的方法论和输出格式。交互确认和增删改操作在 SKILL.md 的 Task 3 中执行。

## 分析流程

```
Step 1  读取 JSON 文件
  └── Agent 读取 JSON 文件内容，获取每个意图及其检索结果

Step 2  分析覆盖情况
  └── 对每个意图，判定其检索结果的覆盖状态

Step 3  输出分析结果
  └── 返回结构化覆盖数据
```

---

## Step 1: 读取 JSON 文件

读取 Task 2 生成的 JSON 文件，文件结构为：

```json
{
  "intent": ["意图1", "意图2", "意图3"],
  "results": [{...}, {...}, {...}]
}
```

- `intent`：当前结果对应的所有意图列表
- `results`：所有检索结果（平铺数组，每条结果包含 title、description 等字段）

---

## Step 2: 分析覆盖情况

根据用户的所有意图，**从全局内容判断**每个意图是否被检索结果覆盖：

**判断逻辑：**

1. 从 JSON 文件的 `intent` 字段获取用户的所有意图
2. 读取 `results` 中所有检索结果的整体内容（不依赖 `sourceIntent` 字段）
3. 对每个用户意图，Agent 从全局视角判断检索结果中是否包含与该意图相关的实质性内容

| 状态 | 判断标准 |
|------|--------|
| `covered` | 检索结果中包含与该意图高度相关的实质性内容 |
| `partial` | 有部分相关内容，但不够充分 |
| `uncovered` | 无相关内容或结果集为空 |

---

## Step 3: 输出分析结果

返回结构化覆盖数据：

```json
{
  "total_intents": 3,
  "is_fully_covered": false,
  "coverage_stats": {
    "covered": 1,
    "partial": 1,
    "uncovered": 1
  },
  "coverage_details": [
    {
      "intent": "意图描述",
      "status": "covered | partial | uncovered",
      "summary": "找到与该意图相关的实质性内容",
      "matched_orders": [3, 5]
    }
  ]
}
```

**字段说明：**
- `matched_orders`：当前意图匹配到的检索结果 order 列表。每条检索结果的 `order` 字段为 str 类型，此处将所有匹配该意图的结果的 `order` 收集为 list

**展示格式（输出给用户）：**

### 📋 意图覆盖情况

**统计**：已覆盖 {N} | 部分覆盖 {N} | 未覆盖 {N}

| # | 意图 (intent) | 覆盖状态 | 说明 |
|---|---------------|---------|------|
| 1 | {intent_1} | ✅ 已覆盖 | {summary} |
| 2 | {intent_2} | ⚠️ 部分覆盖 | {summary} |
| 3 | {intent_3} | ❌ 未覆盖 | {summary} |

> ⚠️ **执行要求**：上表必须实际以 markdown 形式输出给用户看到。

---

## 约束

- [强制] 覆盖分析必须基于 JSON 文件中的实际内容，不得臆断
- [强制] 输出必须包含：是否完全覆盖、每个意图的覆盖状态
