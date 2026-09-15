## 子技能说明

该技能是检索分发的统一入口，根据传入的 `strategy` 参数将检索请求分发到对应的子脚本（知识库 / 联网 / 并行/ 深度检索），并对结果做标准化。

**核心功能**：
- 接收 Agent 传入的参数（query、kb_id、strategy、text-list）
- 按策略分发：
  - `serial` → 调用 `search.py`（知识库检索）
  - `external_only` → 调用 `web_search.py`（联网搜索）
  - `parallel` → 同时调用 `search.py` 与 `web_search.py`，合并结果
  - `deep_only` →  调用 `deep_search.py` (知识库深度检索)
- 标准化输出：统一 `{ success, strategy, results: { markdown, linkMap, overflowFiles, tree_view } }`

**使用场景**：
- 知识库优先检索（教学大纲、产品手册等）
- 纯联网搜索（行业新闻、最新动态）
- 知识库 + 联网并行检索（竞品对比、需要多角度信息）
- 深度检索（文件级别或者挖掘深度内容）
---

## 触发条件

由 SKILL.md 中 Step 4 [CALL] 调用，必须先完成：
1. Step 1 [PREPARE] 获取并选定 `kb_id`
2. Step 2 [REWRITE] 改写 query
3. Step 3 [STRATEGY] 选择 strategy

---

## 不触发条件

1. 缺少 `query`（位置参数为空）
2. `strategy = serial` 或 `parallel` 或 `deep-only` 时 `kb_id` 为空

---

## 参数定义

### CLI 参数

| 参数 | 类型     | 必填                           | 默认值    | 说明                                  |
|------|--------|------------------------------|--------|-------------------------------------|
| query | string | ✅                            | -      | 改写后的检索 query（位置参数 1）                |
| kb_id | string | ✅                            | -      | 知识库 ID，external_only 时可空（位置参数 2）    |
| --strategy | string | ❌                            | serial | 取值：serial / parallel / external_only |
| --text-list | list   | ❌| -      | jSON 数组字符串，3-5 条查询变体  |

---

## [DISPATCH]: 按策略分发

1. 执行逻辑：
   - `strategy = serial` → 调用 `scripts/search.py`
   - `strategy = external_only` → 调用 `scripts/web_search.py`
   - `strategy = parallel` → `ThreadPoolExecutor(max_workers=2)` 并行调用两者
   - `strategy = deep_only` → 调用 `scripts/deep_search.py`
   - 未知策略 → 降级为 `serial`
2. 终止条件：
   - 子脚本失败 → 进入 Step 3 错误处理


