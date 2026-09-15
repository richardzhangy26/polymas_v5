from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "student-survey-profile": {
        "required_terms": [
            "ask_user_question",
            "profile.json",
            "profile.md",
            "schoolId",
            "userId",
            "[CONFIRM]",
        ],
        "forbidden_terms": ["channel_message", "copaw cron"],
    },
    "personalized-learning-feed": {
        "required_terms": [
            "search-router",
            "web-domain-search",
            "channel_message",
            "push_history.jsonl",
            "30 天",
        ],
        "forbidden_terms": ["班级群作为降级", "广播作为降级"],
    },
}


def read(path: Path) -> str:
    assert path.is_file(), f"缺少文件: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def parse_frontmatter(markdown: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", markdown, re.DOTALL)
    assert match, "SKILL.md 缺少 YAML frontmatter"
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip('"')
    return values


@pytest.mark.parametrize("name", PACKAGES)
def test_required_skill_files_exist(name: str) -> None:
    skill_dir = ROOT / name
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / "references" / "data-contract.md").is_file()
    assert (skill_dir / "output_format").is_dir()


@pytest.mark.parametrize("name", PACKAGES)
def test_skill_frontmatter_and_sections(name: str) -> None:
    required_sections = [
        "## 技能说明",
        "## 触发条件 / 不触发条件",
        "## 项目结构",
        "## 执行流程",
        "## 暂停确认规则",
        "## 执行流程强制约束",
    ]
    markdown = read(ROOT / name / "SKILL.md")
    frontmatter = parse_frontmatter(markdown)
    assert frontmatter["name"] == name
    assert frontmatter["description"].startswith("Use when ")
    for section in required_sections:
        assert section in markdown, f"{name} 缺少章节 {section}"


@pytest.mark.parametrize("name", PACKAGES)
def test_skill_responsibility_boundaries(name: str) -> None:
    contract = PACKAGES[name]
    markdown = read(ROOT / name / "SKILL.md")
    for term in contract["required_terms"]:
        assert term in markdown, f"{name} 缺少契约词: {term}"
    for term in contract["forbidden_terms"]:
        assert term not in markdown, f"{name} 出现越界内容: {term}"


def test_assembly_uses_built_in_orchestration() -> None:
    guide = read(ROOT / "EXPERT_GROUP_ASSEMBLY.md")
    for term in [
        "student-survey-profile",
        "personalized-learning-feed",
        "ask_user_question",
        "cron",
        "channel_message",
        "--agent-id",
    ]:
        assert term in guide


def test_no_placeholders_or_sensitive_literals() -> None:
    forbidden_patterns = [
        r"\bTBD\b",
        r"\bTODO\b",
        r"AUTHORIZATION\s*=",
        r"COOKIE\s*=",
        r"Bearer\s+[A-Za-z0-9._-]{16,}",
    ]
    markdown_files = list(ROOT.glob("*/SKILL.md")) + list(
        ROOT.glob("*/references/*.md")
    )
    assert markdown_files, "没有发现待校验的 Skill Markdown"
    for path in markdown_files:
        content = read(path)
        for pattern in forbidden_patterns:
            assert not re.search(pattern, content, re.IGNORECASE), (
                f"{path.relative_to(ROOT)} 命中禁止模式: {pattern}"
            )
