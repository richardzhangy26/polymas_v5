# 个性化简报数据契约

## 输入

从当前学生的 `profile.json` 读取：

```json
{
  "profile_version": 2,
  "identity": {
    "schoolId": "runtime-school-id",
    "userId": "runtime-user-id"
  },
  "questionnaire": {
    "preferred_content_types": ["应用案例", "论文", "学术会议"]
  },
  "recommendation_profile": {
    "primary_topics": ["人工智能"],
    "support_topics": ["数学基础", "科研准备"],
    "content_mix": ["application_case", "learning_resource", "paper", "conference"]
  },
  "consent": {
    "profile_storage": true
  }
}
```

外部检索输入只包含主题词、内容类型、日期范围和语言偏好。

## 候选内容

```json
{
  "content_key": "normalized-url-or-title-date-hash",
  "type": "application_case",
  "title": "候选标题",
  "summary": "一至两句事实摘要",
  "source_name": "来源机构",
  "source_url": "https://example.org/item",
  "published_or_event_at": "ISO-8601 date",
  "review_status": "not_applicable",
  "matched_profile_fields": ["interests", "weak_modules"],
  "scores": {
    "interest_fit": 0,
    "weakness_help": 0,
    "goal_fit": 0,
    "freshness": 0,
    "total": 0
  }
}
```

`type` 允许：`application_case`、`learning_resource`、`paper`、`conference`。

## 评分

```text
total = interest_fit * 0.40
      + weakness_help * 0.30
      + goal_fit * 0.20
      + freshness * 0.10
```

四个分项均为 0—100。来源无法核验、会议已经结束或链接不可用的候选直接淘汰，不参与排序。

## 推送历史

路径：

```text
student_profiles/{schoolId}/{userId}/push_history.jsonl
```

每次成功投递追加一行：

```json
{"content_key":"...","profile_version":2,"sent_at":"ISO-8601 timestamp","delivery":"success"}
```

- 同一 `content_key` 在 30 天窗口内只允许出现一次成功记录。
- 投递失败不追加成功记录；重试由上层任务策略控制。

