import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_plugin_manifest_valid():
    m = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert m["name"] == "report-harness"
    assert "version" in m and "description" in m

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
