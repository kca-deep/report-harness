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
