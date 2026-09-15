"""交付结构与引用契约测试；不代替平台检索联调。"""
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_DATABASE_ENTRIES = {
    "NCBI GenBank", "NCBI BLAST", "NCBI RefSeq", "GSA（国家生物信息中心）",
    "NCBI SRA", "ENA (EMBL-EBI)", "DDBJ", "GWH 基因组仓库",
    "Ensembl", "UCSC Genome Browser", "GENCODE", "TAIR",
    "NCBI GEO", "GEPIA2", "GTEx", "ArrayExpress", "TCGA GDC",
    "UniProt", "RCSB PDB", "AlphaFold DB", "SWISS-MODEL",
    "HPA 人类蛋白图谱", "Pfam", "InterPro",
    "KEGG", "Gene Ontology (GO)", "Reactome", "STRING",
    "dbSNP", "ClinVar", "GeneCards", "DisGeNET",
    "DrugBank", "ChEMBL", "BRENDA", "PubChem",
    "miRBase", "RNAcentral", "IMG", "ViralZone",
    "NCBI Taxonomy", "NGDC 国家生物信息中心",
    "PubMed (NCBI)", "Science", "Web of Science", "Bilibili", "网易公开课",
}


def test_pds_template_and_expansion_match():
    required = {"agent_name", "expertise", "core_responsibilities", "skills", "workflow", "boundaries", "work_style"}
    source = ROOT / "PDS字段.json"
    assert source.exists(), "缺少 PDS 字段权威源"
    fields = json.loads(source.read_text())
    assert set(fields) == required
    template = (ROOT / "Agent.md").read_text()
    assert set(re.findall(r"\$\{(\w+)\}", template)) == required
    rendered = re.sub(r"\$\{(\w+)\}", lambda m: fields[m[1]], template)
    assert rendered == (ROOT / "Agent-完整配置.md").read_text()


def test_skill_references_are_portable_and_resolve():
    skill = ROOT / "bioinfo-db-search"
    assert (skill / "SKILL.md").exists(), "缺少可挂载技能入口"
    entry = (skill / "SKILL.md").read_text()
    assert "name: bioinfo-db-search" in entry
    for path in skill.rglob("*.md"):
        body = path.read_text()
        assert "/Users/" not in body
        for target in re.findall(r"\]\(([^)]+)\)", body):
            if not target.startswith(("https://", "http://", "#")):
                assert (path.parent / target.split("#")[0]).is_file(), (path.name, target)


def test_field_copy_blocks_match_source():
    source = ROOT / "PDS字段.json"
    assert source.exists(), "缺少字段源"
    fields = json.loads(source.read_text())
    document = (ROOT / "PDS字段.md").read_text()
    for key, value in fields.items():
        assert "## ${" + key + "}" in document
        assert "```text\n" + value + "\n```" in document


def test_deep_search_returns_to_expert():
    entry = ROOT / "deep-search" / "SKILL.md"
    assert entry.exists(), "缺少解除子流程停机冲突的兼容版"
    text = entry.read_text()
    assert 'version: "1.0.3-helix.1"' in text
    assert "主专家可继续调用 bioinfo-db-search" in text
    assert "后续操作需要用户另行调用其他 skill" not in text
    for path in (ROOT / "deep-search").rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if not target.startswith(("https://", "http://", "#")):
                assert (path.parent / target.split("#")[0]).is_file(), (path.name, target)


def test_db_routing_covers_every_source_entry():
    """原稿列出的 47 个数据库/资源入口必须全部保留。"""
    routing = (ROOT / "bioinfo-db-search/references/db-routing.md").read_text()
    missing = sorted(name for name in ORIGINAL_DATABASE_ENTRIES if name not in routing)
    assert not missing, f"原稿数据库/资源入口缺失：{missing}"


def test_delivery_zips_contain_current_database_catalog():
    """防止松散文件升级后，上传 ZIP 仍停留在旧版本。"""
    assert not (ROOT / "bioinfo-db-search_0.1.0.zip").exists()
    checks = {
        ROOT / "bioinfo-db-search_0.2.0.zip": (
            "bioinfo-db-search/SKILL.md",
            "bioinfo-db-search/references/db-routing.md",
        ),
        ROOT / "Helix学术检索专家-交付包.zip": (
            "Helix学术检索专家/bioinfo-db-search/SKILL.md",
            "Helix学术检索专家/bioinfo-db-search/references/db-routing.md",
        ),
    }
    for archive, (skill_name, routing_name) in checks.items():
        with zipfile.ZipFile(archive) as package:
            assert package.testzip() is None
            skill = package.read(skill_name).decode()
            routing = package.read(routing_name).decode()
        assert 'version: "0.2.0"' in skill
        missing = sorted(name for name in ORIGINAL_DATABASE_ENTRIES if name not in routing)
        assert not missing, f"{archive.name} 缺失：{missing}"
