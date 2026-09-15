---
name: "student-survey-profile"
description: "Use when a student needs to complete an interest and development questionnaire, create or revise a learning profile, or review the evidence used for personalized recommendations."
---

# Student Survey Profile

## 技能说明

本技能负责“对话式问卷 → 学生确认 → 结构化画像 → 工作区存档”。画像只记录学生主动提供的信息及其来源，不把自评推断成客观能力结论。定时任务、内容检索和消息投递由其他专家或内置能力负责。

## 触发条件 / 不触发条件

### 触发条件

- 学生首次建档、填写兴趣与发展问卷。
- 学生要求查看、补充或修改个人画像。
- 推荐专家发现画像不存在、字段缺失或已经过期。

### 不触发条件

- 仅查询资讯、论文、案例或会议。
- 仅创建、暂停、恢复定时任务。
- 教师要求查看其他学生的完整个人画像，但当前上下文没有相应权限。

## 项目结构

- `references/data-contract.md`：问卷字段、画像结构、路径和版本规则。
- `output_format/profile-report.md`：学生可读的画像报告格式。
- `SKILL.md`：交互、确认、存档和边界规则。

## 执行流程

1. **[DETERMINE] 身份与旧档案**
   - 从可信运行时上下文读取 `schoolId`、`userId`，不得向学生索取技术 ID。
   - 按 `student_profiles/{schoolId}/{userId}/` 查询 `profile.json` 和 `profile.md`。
   - 身份不可唯一确定时，只能生成临时报告，不执行持久化。

2. **[DETERMINE] 复用已知答案**
   - 从学生当前消息和旧画像提取已经明确的信息，不重复询问。
   - 必填字段为：兴趣方向、自评阶段、薄弱模块、未来方向、偏好内容类型。

3. **[CALL] 补齐问卷**
   - 对缺失字段调用内置 `ask_user_question`，每轮合并 1—3 个相关问题。
   - 有稳定候选时提供选项；兴趣、薄弱模块等开放字段允许自定义回答。
   - 工具返回前保持暂停，不用普通文本假装已经获得答案。

4. **[BUILD] 构建画像**
   - 按 `references/data-contract.md` 生成 `profile.json`。
   - 将自评薄弱项标记为 `student_self_report`，并生成可用于检索的推荐主题词。
   - 按 `output_format/profile-report.md` 生成 `profile.md`。

5. **[CONFIRM] 学生核对**
   - 用 `ask_user_question` 展示画像摘要，提供“确认保存”和“继续修改”。
   - 学生选择修改时返回第 3 步；确认后才进入存档。

6. **[BUILD] 幂等存档**
   - 在同一身份目录原位更新 `profile.json` 和 `profile.md`，保留 `created_at`，刷新 `updated_at` 与 `profile_version`。
   - 完成标准：两份文件身份键、版本号和更新时间一致，且能够重新读取。

## 暂停确认规则

- 需要学生补充任何问卷字段时，必须调用 `ask_user_question` 并等待。
- 最终画像必须经过一次可见核对；“继续修改”不得被解释为同意保存。
- 画像保存成功后返回摘要、更新时间和修改方式，不展示内部目录或技术 ID。

## 执行流程强制约束

- `profile.json` 是机器读取的唯一事实源，`profile.md` 是同步生成的可读视图。
- 仅写入当前 `schoolId` 与 `userId` 对应目录；禁止按姓名或学号拼接路径。
- 自评能力、兴趣和规划均保留来源标记，不输出诊断式、决定论式结论。
- 外部检索只能接收脱敏主题词，不能接收姓名、学号或完整画像。
- 本技能的完成状态仅代表“画像已确认并存档”，不代表定时任务或推送已创建。
- 任一步失败时报告实际完成范围，不虚构文件、版本或保存结果。

