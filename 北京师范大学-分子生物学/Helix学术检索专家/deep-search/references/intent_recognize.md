---
name: intent-recognize
description: "交互式意图识别助手。使用 intent_prompt.md 解析用户输入，生成结构化检索意图（retrieval_intents）、文档类型、生成约束和PPT页数，通过交互式确认让用户对检索意图增删改，确认后输出最终 JSON。Use when the user provides a query or task description that needs intent analysis and decomposition before further processing."
---

# 交互式意图识别

## 核心理念

解析用户输入，生成结构化意图识别结果，通过交互确认让用户对 `retrieval_intents` 列表进行增删改，确认后输出最终 JSON。

---

## 执行流程

```
Step 1  读取 intent_prompt.md 作为 prompt 模板
Step 2  执行 prompt 获取 JSON 结果
Step 3  展示 JSON（重点展示 retrieval_intents 列表）
Step 4  [交互] 用户确认 retrieval_intents 列表
        ├─ 确认正确  → 进入 Step 6 输出
        ├─ 需要补充  → 用户描述新意图 → 构造 {intent, searchList} 追加到 list → 回到 Step 3
        ├─ 需要删除  → 用户指定序号 → 从 list 移除该条 → 回到 Step 3
        └─ 需要修改  → 用户指定序号+内容 → 替换 list 中对应条目 → 回到 Step 3
Step 5  循环上限：最多 5 轮调整
Step 6  输出最终确认的 JSON
```

---

## Step 1: 读取 prompt 模板

读取 [references/intent_prompt.md](intent_prompt.md) 获取完整的意图识别 prompt 模板。该模板末尾包含 `%s` 占位符，用于替换用户输入。

---

## Step 2: 执行 prompt 获取 JSON

将 intent_prompt.md 中 prompt 模板末尾的 `%s` 替换为用户原始输入，执行分析，获取 JSON 结果：

```json
{
  "retrieval_intents": [
    {
      "intent": "检索意图描述",
      "searchList": ["关键词1", "关键词2"]
    }
  ]
}
```

> 如果存在 `[待解析]` 标记的意图，说明用户引用了未知资源（如附件、文档章节等），需在展示时特别提示。

---

## Step 3: 展示 JSON 结果

**必须先以文字形式输出以下表格给用户看到，然后再进入 Step 4 调用卡片工具。**

将 JSON 结果以清晰格式展示给用户，**只展示 `retrieval_intents` 列表**：


#### 检索意图列表（retrieval_intents）

| # | 意图 (intent) |
|---|---------------|
| 1 | {intent_1} |
| 2 | {intent_2} |
| 3 | [待解析] {intent_3} |
| ... | ... |

> ⚠️ **执行要求**：上表是必须实际输出给用户的文字内容，不是模板说明。你必须先在对话中以 markdown 形式渲染并输出这个表格，让用户看到后，再去调用 Step 4 的卡片工具。
> 复杂或模糊查询展示后**不要直接输出最终 JSON**，必须进入 Step 4 交互确认；入口允许的简单明确查询可跳过首次确认。

---

## Step 4: 交互确认 [核心]

使用 `AskUserQuestion` 工具确认 `retrieval_intents` 列表：

```
AskUserQuestion:
  questions:
    - question: "以上检索意图列表是否准确？你可以选择补充、删除或修改。"
      header: "确认意图"
      options:
        - label: "确认正确"
          description: "检索意图列表准确，输出最终结果"
        - label: "需要补充"
          description: "需要添加新的检索意图，请在选择后描述意图和关键词"
        - label: "需要删除"
          description: "需要移除某个检索意图，请在选择后说明序号"
        - label: "需要修改"
          description: "需要修改某个检索意图的内容，请在选择后说明序号和修改内容"
```

### 各分支处理

| 用户选择 | 处理逻辑 |
|---------|---------|
| 确认正确 | 进入 Step 6 输出 |
| 需要补充 | 自然语言追问 → 用户描述新意图和关键词 → 构造新的 `{intent, searchList}` 对象 → **追加到 retrieval_intents 数组末尾** → 标注 `[新增]` → 回到 Step 3 重新展示 |
| 需要删除 | 自然语言追问 → 用户指定序号（如"删除第2条"）→ **从 retrieval_intents 数组中移除该索引项** → 标注 `[已删除]` → 回到 Step 3 重新展示 |
| 需要修改 | 自然语言追问 → 用户指定序号和修改内容 → **替换 retrieval_intents 数组中对应项的 intent 或 queries** → 标注 `[已修改]` → 回到 Step 3 重新展示 |

### 补充操作详细规则

1. 追问："请描述需要添加的检索意图，以及相关的检索关键词。"
2. 用户回答后，构造与现有格式一致的对象：`{ "intent": "用户描述的意图", "searchList": ["关键词1", "关键词2", "关键词3"] }`
3. 将该对象**追加**到 `retrieval_intents` 数组末尾
4. 新增项在展示时标注 `[新增]`

### 删除操作详细规则

1. 追问："请说明需要删除第几条检索意图？"
2. 用户回答序号后，从 `retrieval_intents` 数组中**移除指定索引项**
3. 被删除项在展示时保留一行，标注 `[已删除]`
4. 重新编号剩余项

### 修改操作详细规则

1. 追问："请说明需要修改第几条，以及修改为什么内容？"
2. 用户回答后，**替换对应项**的 `intent` 字段或 `searchList` 数组
3. 修改项在展示时标注 `[已修改]`（旧值→新值）

---

## Step 5: 循环上限

- 最多允许 **5 轮** 调整（补充/删除/修改各算 1 轮）
- 达到 5 轮后，输出提示："已达到最大调整次数（5次），将以当前最新结果输出。"
- 进入 Step 6 输出

> 如果用户在确认环节选择"确认正确"则不计入轮次，直接输出。

---

## Step 6: 输出最终结果

输出用户确认后的最终结构化 JSON：

```json
{
  "original_input": "用户原始输入",
  "retrieval_intents": [
    {
      "intent": "检索意图描述",
      "searchList": ["关键词1", "关键词2"]
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `original_input` | string | 用户原始输入 |
| `retrieval_intents` | array | 确认后的检索意图列表（经用户增删改确认） |

---

## 完整示例

### 输入

```
用户输入：刚体的运动写一个10页ppt
```

### Step 1-2 执行 prompt

```json
{
  "retrieval_intents": [
    {"intent": "刚体运动学基本概念与定义", "searchList": ["刚体运动定义", "刚体基本特征", "刚体与质点区别"]},
    {"intent": "刚体定轴转动与角量描述", "searchList": ["转动定律", "角速度", "角加速度"]},
    {"intent": "刚体平面运动分析", "searchList": ["平面运动分解", "纯滚动条件", "刚体动能定理"]}
  ]
}
```

### Step 3 展示

📋 意图识别结果

文档类型：PPT | 生成约束：无 | PPT页数：10

| # | 意图 (intent) |
|---|---------------|
| 1 | 刚体运动学基本概念与定义 |
| 2 | 刚体定轴转动与角量描述 |
| 3 | 刚体平面运动分析 |

### Step 4 交互

用户选择"需要补充" → 追问 → 用户："加一条关于刚体静力学平衡的内容"

→ 构造 `{ "intent": "刚体静力学平衡条件", "searchList": ["力矩平衡", "静力学方程", "约束力分析"] }` 追加到数组末尾

重新展示（4条意图）→ 用户选择"确认正确" → 进入 Step 6

### Step 6 输出

```json
{
  "original_input": "刚体的运动写一个10页ppt",
  "retrieval_intents": [
    {"intent": "刚体运动学基本概念与定义", "searchList": ["刚体运动定义", "刚体基本特征", "刚体与质点区别"]},
    {"intent": "刚体定轴转动与角量描述", "searchList": ["转动定律", "角速度", "角加速度"]},
    {"intent": "刚体平面运动分析", "searchList": ["平面运动分解", "纯滚动条件", "刚体动能定理"]},
    {"intent": "刚体静力学平衡条件", "searchList": ["力矩平衡", "静力学方程", "约束力分析"]}
  ]
}
```

---

## 约束

- [强制] 必须使用 intent_prompt.md 作为 prompt 执行意图识别
- [强制] 复杂或模糊查询的 retrieval_intents 列表必须经用户确认才能输出最终结果；入口 SKILL.md 允许的简单明确查询可跳过该首次确认
- [强制] 每次调整后必须重新展示完整结果，标注变更标记
- [强制] 补充操作必须构造与现有格式一致的 {intent, searchList} 对象
- [强制] 删除操作必须保留删除痕迹（标注 `[已删除]`）
- 最多 5 轮调整，超出后以最新结果输出
- 每轮交互只问一个核心问题
- 补充/删除/修改时用自然语言追问，让用户自由表达
