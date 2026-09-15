"""交付结构与路由契约测试；不代替平台检索联调。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "agent_name",
    "expertise",
    "core_responsibilities",
    "skills",
    "workflow",
    "boundaries",
    "work_style",
}
CREDENTIAL_PATTERNS = (
    r"AUTHORIZATION\s*=",
    r"COOKIE\s*=",
    r"Bearer\s+[A-Za-z0-9._\-]+",
    r"userCloudToken",
)


def fields():
    source = ROOT / "PDS字段.json"
    assert source.exists(), "缺少 PDS 字段权威源"
    data = json.loads(source.read_text(encoding="utf-8"))
    assert set(data) == REQUIRED
    return data


def combined_text():
    parts = [fields()[key] for key in REQUIRED]
    for name in ("Agent.md", "Agent-完整配置.md", "PDS字段.md", "挂载与使用说明.md", "验证记录.md"):
        parts.append((ROOT / name).read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_pds_template_and_expansion_match():
    source_fields = fields()
    template = (ROOT / "Agent.md").read_text(encoding="utf-8")
    assert set(re.findall(r"\$\{(\w+)\}", template)) == REQUIRED
    assert "${agent\\_name}" not in template
    rendered = re.sub(r"\$\{(\w+)\}", lambda m: source_fields[m[1]], template)
    assert rendered == (ROOT / "Agent-完整配置.md").read_text(encoding="utf-8")


def test_field_copy_blocks_match_source():
    source_fields = fields()
    document = (ROOT / "PDS字段.md").read_text(encoding="utf-8")
    for key, value in source_fields.items():
        assert "## ${" + key + "}" in document
        assert "```text\n" + value + "\n```" in document


def test_expert_identity_and_single_skill():
    source_fields = fields()
    assert source_fields["agent_name"] == "大学体育资料检索"
    skills = source_fields["skills"]
    assert "知识检索" in skills
    assert "V0.0.1" in skills
    assert "external-knowledge-search" in skills
    for unrelated in ("班级查询助手", "技能检索", "book"):
        assert unrelated not in skills


def test_course_material_defaults_to_knowledge_search_not_workspace():
    source_fields = fields()
    workflow = source_fields["workflow"]
    boundaries = source_fields["boundaries"]
    text = workflow + "\n" + boundaries
    for token in (
        "知识检索",
        "serial",
        "老师发的",
        "工作空间不能上传 mp4",
        "不以工作空间检索作为默认入口",
    ):
        assert token in text
    assert "先搜工作空间" in workflow or "先搜工作空间" in boundaries


def test_missing_teacher_video_asks_before_public_search():
    workflow = fields()["workflow"]
    for token in (
        "未找到",
        "公开教程",
        "ask_user_question",
        "用户确认前不得",
        "external_only",
        "公开资料",
        "不是老师发布",
    ):
        assert token in workflow


def test_scope_is_locate_materials_only():
    source_fields = fields()
    text = "\n".join(source_fields[key] for key in REQUIRED)
    for token in ("不讲解动作", "不纠正体态", "不制定训练计划"):
        assert token in text
    assert "可点击" in text or "可点击链接" in text


def test_mount_guide_has_opening_questions_and_online_checklist():
    guide = (ROOT / "挂载与使用说明.md").read_text(encoding="utf-8")
    for token in (
        "大学体育资料检索",
        "知识检索",
        "V0.0.1",
        "师生共享",
        "我想看老师发的瑜伽视频",
        "开场白",
        "真实联调清单",
        "未执行",
    ):
        assert token in guide


def test_verification_does_not_claim_online_success():
    record = (ROOT / "验证记录.md").read_text(encoding="utf-8")
    assert "本地" in record
    assert "未执行" in record or "待真实联调" in record
    assert "已经在 PDS 创建" not in record or "不代表已经在 PDS 创建" in record


def test_no_credentials_or_local_user_paths():
    text = combined_text()
    assert "/Users/" not in text
    for pattern in CREDENTIAL_PATTERNS:
        assert re.search(pattern, text) is None
