# Helix 的 Qoder CLI 固定配置测试

这是一个独立测试目录。被测专家作为 Qoder 当前会话的主 Agent 运行，不派生子代理。

## 运行范围

- CLI：本次实际使用 qodercli 1.1.32。
- 正式批次模型：Qwen3.8-Flash，固定名称；模型服务底层版本无法由本地文件锁定。
- 专家：runtime/Expert-source.md，来自 Helix 的完整专家配置。除替换 Qoder frontmatter 外，专家正文没有改写。
- Skill：bioinfo-db-search 0.1.0、deep-search 1.0.3-helix.1、external-knowledge-search 本地来源包标记 1.0.1。
- 可用工具：Read、Glob、Grep、Skill；无 Bash、写入、联网工具、MCP 或 Agent 工具。
- runtime/AGENTS.md 仅说明测试运行环境，不放评分答案。
- 用户问题与合成检索结果由 cases.json 提供；rubric.json 不传给被测专家。
- 每个用例、每次重复均使用全新会话，不恢复历史，不保存可恢复会话。
- 不执行实际 Polymas 脚本、不做数据库联网检索、不改变原专家或平台配置。调用 Qoder 模型本身仍需要网络和账户额度。

## 为什么采用这些设置

只写 skills 白名单不足以在当前 Qoder 的主会话中消除内置与插件技能的可见性。试跑发现额外技能后，已仅在本测试工作区设置 skills.disabled。正式批次的 trace.jsonl 启动事件必须恰好显示三个目标技能，才计为有效测试。

完全独立的 --config-dir 会丢失现有登录态，首轮尝试因此失败。正式批次使用现有 Qoder 登录，不复制凭证；使用 project,local 配置来源、关闭自动记忆并禁用 MCP。

隔离的是技能列表、工具列表和测试数据，不是操作系统容器。Qoder 默认运行框架以及启动日志中的插件包元信息仍可能存在。技能禁用不等于卸载插件。Read 的目录范围通过测试约定限制，本轮另核查调用轨迹；不将其称为操作系统强制沙箱。

runtime 自带独立 Git 根与 codex/helix-test 分支，用于防止向上加载主项目开发规则。只有新测试目录发生变更，原专家与 Skill 作为固定副本保留。tests/run 相关文件在 runtime 外，不放进专家初始提示词。

## 复跑

进入本目录，执行：

```bash
python3 run_tests.py
python3 run_tests.py --case 03_insufficient_papers
python3 run_tests.py --case 05_source_injection --repeat 2
python3 -m unittest discover -s tests -v
```

每次创建新的 runs/日期时间目录。若更改模型或技能，先更新配置再运行，不覆盖历史批次。若登录失效，先在平常使用的 Qoder 环境完成登录；不要把凭证写入本项目。

## 如何读结果

每个用例目录包含：

- input.txt：实际传给专家的内容。
- trace.jsonl：CLI 原始事件，含启动配置、技能与文件读取调用。
- answer.md：最终回答；若模型失败可能是错误信息或空文件。
- result.json：是否得到有效终态、工具轨迹、耗时与 CLI 返回的 credits。
- stderr.txt：CLI 标准错误输出。

批次目录还包含配置哈希 manifest.json、汇总 summary.json 和完整运行后生成的 integrity.json。环境或模型执行错误会停止批次，明确不计为通过；查明原因后另开新批次。

completed 仅表示模型正常返回，不表示专家回答合格。environment_ok 表示工具和技能名单符合要求。内容成绩由 rubric.json 逐条对照 answer.md 和 trace.jsonl 评定。本次评审由当前助手执行，没有额外独立评审模型。

## 这轮不能证明的能力

真实数据库检索成功率、Polymas 登录权限、脚本可执行性、工具实际参数映射、交互问答工具能否暂停、多轮状态继承、线上模型效果、完整系统综述能力均未由此测试验证。

合成数据使用 example.org 测试链接以及 MOCK 标题，均非真实学术证据。报告只评估专家如何处理这些材料，不能当作学术检索结果使用。
