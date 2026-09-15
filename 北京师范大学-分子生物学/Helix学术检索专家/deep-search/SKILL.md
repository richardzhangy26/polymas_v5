---
name: deep-search
description: "三阶段完整流程：意图识别→深度检索→覆盖检查。解析用户输入生成检索意图，调用 deep_search.py 执行检索，再分析意图覆盖情况供用户交互调整。Use when the user provides a query that needs intent analysis, deep search, and coverage check."
metadata:
  version: "1.0.3-helix.1"
---

# 意图识别 → 深度检索 → 覆盖检查

## 子流程职责与返回边界

本版基于用户提供的 1.0.3 来源包做文档适配，脚本运行逻辑未修改，仅规范化继承的尾随空白。负责意图识别、检索、覆盖检查，然后返回主专家。主专家可继续调用 bioinfo-db-search 核验证据并整理用户已请求的检索答案；本技能自身不生成 PPT、论文或独立文档。

本节中的“终止”只指本检索子流程结束，不终止主专家已获授权的任务。后续新增上传、发送、订阅等行为不因本次检索获得授权。

数据源范围由用户条件确定并在所有初次检索、新增、全部重检和部分重检时显式传递同一 --action_list。示例中的 action_list_json 始终采用已确认的来源范围；不得依赖脚本默认值导致“不联网”条件丢失。范围变更需用户明确请求。

文档中的 AskUserQuestion 是交互占位名称，执行时使用平台真实暴露且已验证映射的 ask_user_question；没有该工具时返回待确认状态，不能用普通文本假装已完成交互或自动代选。

## 核心理念

三阶段串联流程：

- **Task 1 意图识别**：读取 references/intent_recognize.md 执行意图识别 → Agent 判断是否需要用户确认（简单 query 可跳过）→ 用户确认
- **Task 2 深度检索**：基于确认的检索意图 → 调用 deep_search.py → 结果自动写入 JSON 文件
- **Task 3 覆盖检查**：读取 references/coverage_check.md 执行覆盖分析 → 交互调整（含回环重新检索）→ 返回最终结果

---

## 流程总览

```
Task 1  意图识别
  └── 读取 references/intent_recognize.md 执行完整流程

Task 2  深度检索
  ├── 将 retrieval_intents 整体传递给 deep_search.py '{retrieval_intents_json}' --raw_query "{用户原query}"
  └── 结果自动写入 JSON 文件（文件名内部生成）→ 传递文件路径给 Task 3

Task 3  覆盖检查与交互调整
  ├── ① 执行覆盖检查（读取 coverage_check.md 分析逻辑）
  ├── ② 更新 JSON 文件（写入标注结果）→ 展示结果给用户
  ├── ③ 用户确认 → 输出最终结果，流程结束
  ├── ③ 用户删除意图 → update_result.py --op delete → 展示剩余意图表 → 继续交互
  ├── ③ 用户新增意图 → deep_search.py --op add --json_file → 回到 ①
  └── ③ 用户重新搜索 → deep_search.py --op replace_all/replace_intents --json_file → 回到 ①
```

---

## Task 1: 意图识别

读取 [references/intent_recognize.md](references/intent_recognize.md) 并严格按照其中的执行流程、步骤和案例完成意图识别。

**确认策略**：Agent 根据用户 query 的复杂度自主判断是否需要用户确认：
- **简单 query**（意图明确、主题单一，如“刚体运动的ppt”）：Agent 直接生成 `retrieval_intents` 并跳过用户确认，直接进入 Task 2
- **复杂/模糊 query**（主题宽泛、指代不清、涉及多个领域）：按 intent_recognize.md 中的完整交互流程，展示意图列表并请求用户确认

用户确认后（或 Agent 判断跳过确认），将最终的 `retrieval_intents` 列表传递给 Task 2。

---

## Task 2: 深度检索

> **脚本路径**：检索脚本位于项目根目录 `scripts/`。下文 `{scripts_dir}` 指代该目录。

> **输出方式**：`deep_search.py` 内部自动生成文件名（格式：`{当前时间}_{意图描述}.json`），检索结果直接写入该文件，不经过 Agent 透传。

执行逻辑：将 Task 1 确认的 `retrieval_intents` 列表**整体**作为位置参数传递给 `scripts/deep_search.py`，同时传入 `--raw_query` 用于生成文件名。
**`--action_list` 数据源选择规则：**
Agent 根据用户 query 中的关键词判断传递哪个数据源：

| 用户表述 | `--action_list` 值 |
|---------|-------------------|
| 未指定数据源（默认） | `["db_search","internet"]` |
| 指定联网/搜索互联网 | `["internet"]` |
| 指定只走知识库/不联网 | `["db_search"]` |
```bash
cd {scripts_dir} && python3 deep_search.py '{retrieval_intents_json}' --raw_query "{用户原始query}" --action_list '{action_list_json}'
```

**参数说明：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 位置参数 | Task 1 确认的完整 `retrieval_intents` 列表（JSON 格式，每个元素含 `intent` 和 `searchList`） | 必填 |
| `--raw_query` | 用户原始 query（用于生成输出文件名） | 必填 |
| `--action_list` | 数据源列表（根据用户是否指定联网/知识库决定） | `["db_search","internet"]` |

**stdout 输出：**

脚本仅输出执行状态（小 JSON），不含检索结果本身：

```json
{"success": true, "output": "scripts/20250720_143052_刚体运动学基本概念.json"}
```

**Agent 操作步骤：**

1. 根据用户 query 判断数据源，确定 `action_list`
2. 调用 `deep_search.py '[{"intent":"...","searchList":[...]}]' --raw_query '用户原始query' --action_list '{action_list}'`
3. 检查 stdout 确认 `success: true`，获取 `output` 字段中的文件路径
4. 将该 JSON 文件路径传递给 Task 3

> 如果 stdout 中 `success` 为 `false`，直接终止流程并告知用户检索失败。

**示例：**

```bash
cd {scripts_dir} && python3 deep_search.py '[{"intent":"刚体运动学基本概念","searchList":["刚体运动定义","刚体运动类型"]},{"intent":"刚体定轴转动定律","searchList":["转动定律","角动量守恒"]}]' --raw_query "刚体的运动写一个ppt" --action_list '["db_search","internet"]'
# stdout: {"success": true, "output": "scripts/20250720_143052_刚体的运动写一个ppt.json"}
# 检索结果已自动写入该文件
```

---

## Task 3: 覆盖检查与交互调整

Task 3 的输入是 Task 2 生成的 JSON 文件路径。Task 3 采用“检查→展示→操作→再检查”的循环模式，直到用户确认满意。

### 涉及的脚本

| 脚本 | 用途 |
|------|------|
| `update_result.py` | 删除意图/更新文件数据 |
| `deep_search.py` | 新增意图 / 重新检索（通过 `--op` 和 `--json_file` 直接更新 JSON） |

### Task 3 循环流程

```
循环开始 ──→ ① 执行覆盖检查 ──→ ② 更新 JSON 文件 ──→ ③ 展示结果给用户 ──→ ④ 用户选择操作
  ↑                                                                          │
  │    ┌──────────────────────────────────────────────────────────┘
  │    ├── 确认满意   → 输出最终结果，流程结束
  │    ├── 删除意图   → update_result.py --op delete --intent "{意图}" → 展示剩余意图表 → 回到 ③
  │    ├── 新增意图   → deep_search.py '{新意图JSON}' --json_file {json_file} --op add → 回到 ①
  │    ├── 全部重检   → deep_search.py '{意图列表JSON}' --json_file {json_file} --op replace_all → 回到 ①
  │    └── 部分重检   → deep_search.py '{对齐后意图JSON}' --json_file {json_file} --op replace_intents → 回到 ①
```

### ① 执行覆盖检查

读取 [references/coverage_check.md](references/coverage_check.md) 中的分析逻辑，Agent 读取 JSON 文件内容，执行 Step 1 ~ Step 4，返回结构化覆盖分析结果（JSON 格式）。

> ⚠️ coverage_check.md 只负责分析并返回结果，不操作文件，不与用户交互。

### ② 更新 JSON 文件

调用 `update_result.py --op annotate_intents`，将 ① 返回的 `coverage_details` 中的意图标注写回 JSON 文件：

```bash
cd {scripts_dir} && python3 update_result.py --file {json_file_path} --op annotate_intents --annotation-data '{coverage_json}'
```

> `{coverage_json}` 是 ① 返回的完整 JSON 字符串（包含 `coverage_details` 和 `matched_orders`），脚本会根据 `matched_orders` 反向映射，为每条结果写入 `intent` 字段。

### ③ 展示结果给用户

以表格形式展示每个意图的覆盖状态，**每个意图必须带编号和 intent 描述**，方便用户准确识别：

### 📋 意图覆盖情况

**统计**：已覆盖 {N} | 部分覆盖 {N} | 未覆盖 {N}

| # | 意图 (intent) | 覆盖状态 | 说明 |
|---|---------------|---------|------|
| 1 | 刚体运动学基本概念 | ✅ 已覆盖 | 找到与该意图相关的实质性内容 |
| 2 | 刚体定轴转动定律 | ⚠️ 部分覆盖 | 有部分相关内容，但不够充分 |
| 3 | 角动量守恒定律 | ❌ 未覆盖 | 无相关内容 |

> ⚠️ **执行要求**：必须实际以 markdown 形式输出给用户看到。用户后续通过意图名称来指定操作目标（如“删除刚体运动学那个”）。

### 📋 检索结果保存路径

检索在工作空间的路径为：{json_file_path}

### ④ 用户选择操作

使用 `AskUserQuestion` 工具确认覆盖情况：

```
AskUserQuestion:
  questions:
    - question: "检索意图已覆盖<具体覆盖的意图>？你可以选择删除未搜到的意图、新增意图或重新搜索。返回给用户确认"
      header: "确认覆盖"
      options:
        - label: "确认满意"
          description: "覆盖情况符合预期，输出最终结果"
        - label: "删除意图"
          description: "删除某个检索意图，请在选择后说明意图名称"
        - label: "新增检索意图"
          description: "添加新的检索意图，请在选择后描述意图和关键词"
        - label: "重新搜索某意图"
          description: "对某个意图重新执行检索，请在选择后说明意图名称"
```

#### 分支 A：确认满意

流程结束，读取当前 JSON 文件内容，向主 Agent 返回最终结果：

```json
{"success": true, "output": "{json_file_path}"}
```

> - `output`：当前 JSON 文件的绝对路径

#### 分支 B：删除意图

1. 追问：“请说明需要删除哪个意图？”
2. 用户回答后，Agent 将用户输入与 JSON 中的实际意图进行语义对齐，找到最匹配的意图，调用 `update_result.py`：
```bash
cd {scripts_dir} && python3 update_result.py --file {json_file_path} --op delete --intent "{对齐后的意图}"
```

5. 告知用户：“意图 [{对齐后的意图}] 已删除”，并展示剩余意图表
6. 继续交互（回到 ③）

#### 分支 C：新增检索意图

1. 追问：“请描述需要添加的检索意图。”
2. 用户回答后，Agent 根据意图描述自动改写并拆解为 `searchList`（多个检索关键词）
3. 直接调用 `deep_search.py` 执行检索，传入 JSON 文件路径让其直接更新：

```bash
cd {scripts_dir} && python3 deep_search.py '[{"intent":"{新意图}","searchList":["关键词1","关键词2"]}]' --raw_query "{新意图}" --json_file {json_file_path} --op add --action_list '{action_list_json}'
```

> deep_search.py 内部自动完成：检索 → 读取已有 JSON → 追加新意图和新结果 → 去重 + 重排 order → 写回文件。

4. 回到 ① 重新检查覆盖

#### 分支 D：重新搜索

1. 追问：“您需要全部重新检索还是部分重新检索？”
2. 根据用户回答进入不同分支：

##### D1：全部重新检索

用户希望对所有意图重新检索：

```bash
cd {scripts_dir} && python3 deep_search.py '{意图列表JSON}' --raw_query "{原query}" --json_file {json_file_path} --op replace_all --action_list '{action_list_json}'
```

> `--op replace_all` 表示清空旧结果，用新检索结果全量替换（内部自动去重 + 重排 order）。

回到 ① 重新检查覆盖

##### D2：部分重新检索

1. 追问：“请说明需要重新搜索哪些意图？”
2. 用户回答后，Agent 将用户输入与 JSON 中的实际意图进行语义对齐
3. 向用户确认：“您想重新搜索的是：{对齐后的意图列表}，确认吗？”
4. 用户确认后，调用 `deep_search.py`，传入需要对齐替换的意图列表：

```bash
cd {scripts_dir} && python3 deep_search.py '{对齐后的意图列表JSON}' --raw_query "{原query}" --json_file {json_file_path} --op replace_intents --action_list '{action_list_json}'
```

> `--op replace_intents` 表示删除指定意图的旧结果，加入新结果（内部自动去重 + 重排 order）。

回到 ① 重新检查覆盖

> 循环最多 5 轮，超出后以最新结果输出最终结论。

---

## 约束

### 流程约束
- [强制] 必须按 Task 1 → Task 2 → Task 3 顺序执行
- [强制] Task 1 必须读取 references/intent_recognize.md 执行
- [强制] Task 1 对于复杂/模糊 query 必须经用户确认才能进入 Task 2，简单 query 可由 Agent 自主判断跳过确认
- [强制] Task 3 最终输出必须返回给主 Agent：`{"success": true/false, "output": "{json_file_path}"}`
- [强制] Task 2 调用时必须传 --raw_query 参数
- [强制] Task 3 覆盖检查必须读取 references/coverage_check.md 的分析逻辑
- [强制] Task 3 删除意图通过 update_result.py --op delete 执行，操作以 --intent 定位
- [强制] Task 3 新增意图通过 deep_search.py --op add --json_file 直接更新 JSON
- [强制] Task 3 重新检索通过 deep_search.py --op replace_all/replace_intents --json_file 直接更新 JSON
- [强制] Task 3 每次操作后必须重新执行覆盖检查并展示给用户
- [强制] Task 3 展示给用户时必须明确声明：是否完全覆盖、已覆盖意图列表、未覆盖意图列表
- [强制] 新增意图时必须构造与现有格式一致的 {intent, searchList} 对象


### 边界约束

- Task 3 完成后，本技能立即向主专家返回真实结果文件与覆盖状态，不继续发起检索或生成新内容。
- 主专家读取实际结果后可继续执行已请求的领域核验与证据整理，无需用户另开一轮请求。
- 本技能自身不生成 PPT、论文或投稿文件，不执行任何发布、上传或消息发送。
- 不把检索 success 等同于证据充分；主专家按领域规则检查原始链接、对象与可见范围。
- 初次和后续所有检索必须保留用户指定的来源范围，不联网时一律显式传 --action_list '["db_search"]'。
