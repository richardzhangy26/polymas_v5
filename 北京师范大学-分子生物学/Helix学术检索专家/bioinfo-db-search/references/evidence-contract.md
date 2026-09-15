# 检索计划与证据契约

这些字段是主专家与领域技能之间的逻辑结构，不是检索 API 的新增参数。仅有方案时返回 plan；有实际材料后才返回 review。

## Plan 必备内容

- mode：plan。
- question：用户原始问题。
- constraints：实体原名与已核实标识、物种、数据类型、时间起止及字段、来源范围、数量；不适用记“不适用”，待确认记“待确认”。
- queries：候选查询式、目标来源和选择理由。尚未执行的查询使用 planned 标记。
- inclusion／exclusion：纳入、排除条件；用户无特殊要求时按主题相关、对象一致、来源可追溯筛选。
- questions：仅列会改变对象或权限范围的待确认问题。
- status：planned 或 needs_clarification。

## Review 必备内容

保持 plan 条件；另记录实际执行的查询、执行时间与时区、检索后端、访问或工具错误。拿不到执行时间时写“未知”，不把编写配置的日期当作执行日期。

每条 evidence 记录包含以下字段；缺失值填“未提供／未核验”，不推测：

| 字段 | 含义 |
|---|---|
| evidence_id | 本轮唯一引用编号 |
| source_type | database_record／paper／course_material／secondary |
| title、source_name、url | 原始标题、来源名、实际返回的来源链接；无链接的内容不得伪造 |
| identifiers | DOI、PMID、Accession、数据集或通路 ID，按实际取得填写 |
| entity、species | 记录对应对象和物种；主题文献可以不适用 |
| version | 记录版本、isoform、assembly 等适用信息 |
| published_or_updated_at、retrieved_at | 来源显示的发表／更新时间与实际获取时间，分开记录 |
| visibility | original_record／full_text／abstract／search_snippet／link_only |
| evidence_kind | 实验、计算预测、原始研究、综述、预印本、课程说明等来源明确的类型 |
| supported_claim | 实际可见材料支持的具体陈述，附可定位摘要句意或段落；不要编造引文 |
| limitations | 片段结构、物种差异、摘要可见、样本未知、冲突等 |
| decision、reason | included／candidate／excluded 及理由 |

主专家可以用自然语言维护这些记录，不强制输出大段 JSON 给用户。

## 核验顺序

1. **来源与可见性**：核对实际返回 URL 的来源身份及标题，不以首页或搜索结果页冒充条目。搜索片段只支持发现候选；缺少关键字段的摘要也只能作为候选。仅当摘要中确有相应陈述且元数据满足条件时，可按“摘要证据”有限纳入，不声称读过全文。
2. **对象与版本**：确认物种、符号、稳定 ID、转录本与组装版本；不跨物种合并，不把一个 isoform 推广到全部。暂无法确认身份的结果保留为 candidate。
3. **文献纳入**：核实日期和文章类型。综述不计入原始研究；预印本标明未经正式同行评审发表的状态；搜索工具标签不足以断言撤稿或未撤稿，相关状态只按实际核验写。
4. **生物学解释**：预测与实验分栏；相关性与因果区分；单篇或单一模型结果不过度外推；数据库注释与直接实验支持分开表述。
5. **去重与冲突**：优先 DOI／PMID 或 Accession＋版本去重；同一论文出现在多站仍是一份证据。版本不同或结论冲突保留并列，注明条件差异，不静默选“看起来更正确”的一条。
6. **覆盖与数量**：仅 included 计入满足要求数量；candidate 单列。覆盖按用户子问题逐项说明，工具 success=true 或数量足够均不能替代证据核验。

## 状态

| status | 使用条件 |
|---|---|
| planned | 只生成方案，尚未检索 |
| needs_clarification | 关键对象或来源选择待用户确认 |
| completed | 本轮要求已由适格证据覆盖；只指本轮，不代表穷尽领域文献 |
| partial | 有适格结果，但数量、子问题、字段或专业整合尚有缺口 |
| no_results | 查询实际执行成功，在记录的条件与本轮来源内未找到适格证据 |
| tool_unavailable | 能力未挂载、认证／权限不足、执行失败、文件不可读或响应无法解析 |

失败不能写 no_results；no_results 不能解释为学术界不存在相关研究。上游缺口可保留原因列表，展示时使用清楚的中文，不暴露凭证、身份上下文或内部错误堆栈。
