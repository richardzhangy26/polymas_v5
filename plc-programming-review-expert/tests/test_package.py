"""交付结构与路由契约测试；不代替平台审查联调。"""
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
    for name in (
        "Agent.md",
        "Agent-完整配置.md",
        "PDS字段.md",
        "挂载与使用说明.md",
        "验证记录.md",
        "需求与决策记录.md",
        "能力选型表.md",
        "学生使用案例.md",
    ):
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
    assert source_fields["agent_name"] == "PLC编程审查"
    skills = source_fields["skills"]
    assert "文件理解" in skills
    assert "resource-understanding" in skills
    assert "知识检索" in skills and "不挂「知识检索」" in skills
    for unrelated in ("plc-code-review", "班级查询助手", "技能检索"):
        assert unrelated not in skills


def test_text_reviews_without_skill_file_calls_understanding():
    source_fields = fields()
    text = source_fields["workflow"] + "\n" + source_fields["core_responsibilities"]
    assert "不调用技能" in text or "不调用本技能" in source_fields["skills"]
    assert "文件理解" in text
    assert "resource-understanding" in text
    assert "无法判定" in text


def test_review_contract_and_safety_boundary():
    source_fields = fields()
    text = "\n".join(source_fields[key] for key in REQUIRED)
    for token in (
        "P0",
        "P1",
        "P2",
        "最小正确片段",
        "硬件安全回路",
        "不提供完整可下装程序",
        "不打分",
        "西门子",
    ):
        assert token in text


def test_zero_new_skill_in_selection_table():
    table = (ROOT / "能力选型表.md").read_text(encoding="utf-8")
    assert "零新 Skill" in table
    assert "plc-code-review" in table
    assert "v1 不挂" in table


def test_mount_guide_has_opening_questions_and_online_checklist():
    guide = (ROOT / "挂载与使用说明.md").read_text(encoding="utf-8")
    for token in (
        "PLC编程审查",
        "文件理解",
        "resource-understanding",
        "开场白",
        "真实联调清单",
        "未执行",
        "帮我审作业",
    ):
        assert token in guide


def test_student_cases_exist_outside_agent_prompt():
    cases = (ROOT / "学生使用案例.md").read_text(encoding="utf-8")
    agent = (ROOT / "Agent-完整配置.md").read_text(encoding="utf-8")
    assert "电机正反转缺互锁" in cases
    assert "不要把本文件贴进 PDS 提示词" in cases
    assert "MotorFwd := TRUE" not in agent


def test_verification_does_not_claim_online_success():
    record = (ROOT / "验证记录.md").read_text(encoding="utf-8")
    assert "本地" in record
    assert "未执行" in record or "待真实联调" in record
    assert "不代表已经在 PDS 创建" in record


def test_no_credentials_or_local_user_paths():
    text = combined_text()
    assert "/Users/" not in text
    for pattern in CREDENTIAL_PATTERNS:
        assert re.search(pattern, text) is None
