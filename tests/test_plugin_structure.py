import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_plugin_manifest_valid():
    m = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert m["name"] == "report-harness"
    assert "version" in m and "description" in m


def test_marketplace_manifest_valid():
    mk = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert mk["name"] and mk["description"] and mk["owner"]["name"]
    entries = [p for p in mk["plugins"] if p["name"] == "report-harness"]
    assert len(entries) == 1, "report-harness 항목이 정확히 하나여야 한다"
    assert entries[0]["source"] == "./", "저장소 루트를 플러그인으로 등록한다"


def test_marketplace_version_matches_plugin():
    """배포 시 두 매니페스트의 버전이 어긋나면 설치본과 카탈로그가 불일치한다."""
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    mk = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    entry = next(p for p in mk["plugins"] if p["name"] == "report-harness")
    assert entry["version"] == plugin["version"], (
        f"marketplace.json {entry['version']} != plugin.json {plugin['version']}"
    )

def test_research_skill_exists():
    t = (ROOT / "skills/report-research/SKILL.md").read_text(encoding="utf-8")
    assert t.startswith("---") and "name: report-research" in t
    assert "_manifest.jsonl" in t and "확정" in t

def test_pipeline_skill_references_exist():
    t = (ROOT / "skills/report-pipeline/SKILL.md").read_text(encoding="utf-8")
    for ref in ["style-guide.md", "md-profile.md", "hwpx-recipe.md", "diagram-pool.md",
                "format-profile.kca.md", "rules-seed.md", "lint_md_profile.py", "harness_config.py"]:
        assert ref in t, ref
    for f in ["style-guide.md", "md-profile.md", "hwpx-recipe.md", "rules-seed.md"]:
        assert (ROOT / "skills/report-pipeline/references" / f).is_file()

def test_commands_and_bundle():
    for c in ["report-research", "report-analyze", "report-draft", "report-export"]:
        assert (ROOT / "commands" / f"{c}.md").is_file()
    assert (ROOT / "skills/humanizer/SKILL.md").is_file()
