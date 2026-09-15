# 学生问卷与画像数据契约

## 存储位置

```text
student_profiles/{schoolId}/{userId}/
├── profile.json
└── profile.md
```

- `schoolId`、`userId` 只从可信运行时上下文取得。
- 路径不得包含姓名、学号、手机号或学生自由输入内容。
- 更新采用原位替换；同一学生不得因重复运行产生平行档案。

## 必填问卷字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `interests` | 字符串数组 | 学生主动选择或填写的兴趣方向 |
| `self_assessed_level` | 枚举 | `beginner`、`developing`、`proficient` |
| `weak_modules` | 字符串数组 | 学生自评薄弱模块，不代表客观诊断 |
| `development_goals` | 字符串数组 | 就业、升学、科研、竞赛、创业、尚未确定等 |
| `preferred_content_types` | 字符串数组 | 应用案例、学习资源、论文、学术会议 |

## `profile.json`

```json
{
  "schema_version": 1,
  "profile_version": 1,
  "identity": {
    "schoolId": "runtime-school-id",
    "userId": "runtime-user-id"
  },
  "questionnaire": {
    "version": "mvp-1",
    "interests": ["人工智能"],
    "self_assessed_level": "developing",
    "weak_modules": ["数学基础"],
    "development_goals": ["升学"],
    "preferred_content_types": ["应用案例", "论文", "学术会议"]
  },
  "evidence": {
    "weak_modules": "student_self_report",
    "development_goals": "student_self_report"
  },
  "recommendation_profile": {
    "primary_topics": ["人工智能"],
    "support_topics": ["人工智能数学基础", "研究生科研准备"],
    "content_mix": ["application_case", "learning_resource", "paper", "conference"]
  },
  "consent": {
    "profile_storage": true,
    "confirmed_at": "ISO-8601 timestamp"
  },
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp"
}
```

## 更新规则

1. 保留 `created_at`，每次确认后递增 `profile_version`。
2. 新回答覆盖对应字段，未被询问的有效字段保持不变。
3. 学生要求删除画像时，由具备删除权限的上层专家执行；本技能只返回明确的删除请求状态。
4. 推荐专家只读取 `recommendation_profile`、内容偏好和必要的来源标记。

