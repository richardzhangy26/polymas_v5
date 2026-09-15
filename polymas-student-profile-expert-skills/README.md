# 学生问卷画像与定制推送 Skills

本目录包含两个可分别上传、由专家团编排的专业 Skill：

- `student-survey-profile`：问卷与画像。
- `personalized-learning-feed`：画像驱动的检索、推荐与单学生投递。

AI 助教内置的 `ask_user_question`、`cron`、`channel_message`、`search-router`、`web-domain-search` 不重复打包。

## 上传

使用 `dist/` 中的两个 ZIP 分别上传到技能池并启用，然后按 `EXPERT_GROUP_ASSEMBLY.md` 创建三位专家和专家团。

## 本地校验

```bash
python -m pytest -q polymas-student-profile-expert-skills/tests/test_skill_packages.py
```

## 线上验证重点

- 当前学生身份是否能在定时执行时恢复。
- `channel_message` 是否能唯一定位该学生会话。
- `cron` 创建后是否返回并可查询下一次执行时间。
- 工作区文件是否按学生身份隔离。
