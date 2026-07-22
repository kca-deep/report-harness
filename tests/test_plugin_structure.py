import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_plugin_manifest_valid():
    m = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert m["name"] == "report-harness"
    assert "version" in m and "description" in m
