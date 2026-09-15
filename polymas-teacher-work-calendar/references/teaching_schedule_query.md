---
name: "polymas-teacher-work-calendar-query"
description: "工作日历查询：查教学日程（课程/会议/作业截止/考试/AI提醒）"
---

## 技能说明

该技能为教师用户提供工作日历查询服务，支持按时间范围和事件类型筛选教学日程。

**用户角色**：仅限教师用户使用

| 核心能力 | 说明 |
|---------|------|
| 日程查询 | 按时间范围查询教学日程（课程/会议/作业截止等） |
| 类型筛选 | 按日历/作业/考试/AI提醒分类查询 |
| 近期查询 | 不指定日期，查询最近的日程安排 |

---

## 工具1：get_teaching_schedule.py — 教学日程查询

### 参数定义

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| type | int | 否 | 0 | 事件类型：0=日历 1=作业 2=考试 3=AI提醒 |
| startDate | string | 否 | 今天 | 开始日期（格式: yyyy-MM-dd，未传默认今天） |
| endDate | string | 否 | 同 startDate | 结束日期（格式: yyyy-MM-dd，未传默认同开始日期） |
| sortId | int | 否 | 自动推断 | 排序ID（不能传 0，否则查不出数据；未指定时脚本按日期自动推断，见 sortId 使用说明） |
| limit | int | 否 | 20 | 返回数量限制 |

### 执行命令

按日期范围查询：

```bash
python3 scripts/get_teaching_schedule.py --type 0 --start-date "2026-07-20" --end-date "2026-07-26"
```

查近期数据（不传日期时脚本默认查询今天，自动使用 sortId = 1）：

```bash
python3 scripts/get_teaching_schedule.py --type 0 --limit 10
```

### type 枚举说明

| 值 | 含义 | 典型场景 |
|----|------|---------|
| 0 | 日历 | 综合查看所有日程（课程、会议、作业截止等） |
| 1 | 作业 | 只看作业相关安排和截止 |
| 2 | 考试 | 只看考试安排 |
| 3 | AI提醒 | 只看AI智能提醒 |

### sortId 使用说明

**sortId 不能传 0，否则接口查不出数据**；日期参数也不能为空，否则后端报 SQL 错误（Incorrect DATE value: ''）。未显式指定 `--sort-id` 时，脚本按日期范围自动推断（未传日期时脚本自动填充 startDate=endDate=今天）：

| 场景 | sortId | 说明 |
|------|--------|------|
| 显式指定 `--sort-id` | 指定值 | 优先使用显式值 |
| 未传日期（默认今天） | 1 | 脚本自动填充 startDate=endDate=今天，查今天及未来 |
| 日期范围整体在过去（结束日期早于今天） | -1 | 往上划找之前的（更早的日程），配合 limit 使用 |
| 今天及未来（含跨今天范围） | 1 | 往下滑找之后的（更新的日程），配合 limit 使用 |

### 时间范围转换规则

Agent 需要将用户的自然语言时间表述转换为 `yyyy-MM-dd` 格式：

| 用户表述 | startDate | endDate |
|---------|-----------|----------|
| 今天 | {今天日期} | {今天日期} |
| 明天 | {明天日期} | {明天日期} |
| 后天 | {后天日期} | {后天日期} |
| 本周 | {本周一日期} | {本周日日期} |
| 下周 | {下周一日期} | {下周日日期} |
| 本月 | {本月1日} | {本月最后一天} |
| 最近/近期 | 不传 | 不传（脚本默认今天，自动 sortId = 1 + limit） |

### 返回结构

```json
{
  "code": 200,
  "data": [
    {
      "scheduleId": "String，日程ID",
      "scheduleName": "String，日程名称",
      "scheduleType": "Integer/String，日程类型",
      "scheduleDate": "String，日程时间",
      "location": "String，地点（教室等）",
      "courseName": "String，关联课程名称",
      "status": "String，状态",
      "description": "String，描述/备注"
    }
  ]
}
```

---

## 数据依赖关系

```
Agent 解析时间/类型 ──→ sortId, type, startDate, endDate, limit
                              │
工具1 get_teaching_schedule ←── 参数  ──→ 日程列表
                              │
Agent 格式化展示 ←── 日程数据
```

---

## 执行流程

### Step 1 [PARSE]：解析时间范围

将用户自然语言时间描述转换为 startDate / endDate：
- 明确时间表述 → 转为具体日期范围
- "最近/近期" → 不传日期（脚本默认今天，自动 sortId = 1 + limit）
- 未指定时间 → 默认今天

### Step 2 [PARSE]：解析事件类型

根据用户意图映射 type 值：
- 综合/所有安排 → type = 0
- 作业 → type = 1
- 考试 → type = 2
- AI 提醒 → type = 3

### Step 3 [EXECUTE]：调用查询

执行 `get_teaching_schedule.py`，传入解析后的参数。

### Step 4 [BUILD]：构造响应

根据返回数据按时间排序展示，格式见 `output_format/teaching_schedule_output_format.md`。
