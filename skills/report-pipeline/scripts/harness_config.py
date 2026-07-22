"""설정 로드·작업폴더 규약 (spec §2·§3). stdlib-only."""
import json, pathlib, datetime

DEFAULT_CONFIG_PATH = pathlib.Path.home() / ".claude" / "report-harness.json"

def load_config(path=None):
    path = pathlib.Path(path) if path else DEFAULT_CONFIG_PATH
    raw = {}
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
    def p(key, default):
        val = raw.get(key)
        return pathlib.Path(val).expanduser() if val is not None else default
    return {
        "reports_dir": p("reports_dir", pathlib.Path.cwd() / "reports"),
        "state_dir": p("state_dir", pathlib.Path.home() / ".claude" / "report-harness-state"),
        "knowledge_vault": p("knowledge_vault", None),
        "template_hwpx": p("template_hwpx", None),
    }

def work_dir(config, slug, now=None):
    now = now or datetime.datetime.now()
    d = pathlib.Path(config["reports_dir"]) / now.strftime("%Y%m%d") / f"{now.strftime('%H%M')}_{slug}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def state_paths(config):
    sd = pathlib.Path(config["state_dir"])
    sd.mkdir(parents=True, exist_ok=True)
    return {"rules": sd / "rules.md", "lessons": sd / "lessons.jsonl", "state_dir": sd}

if __name__ == "__main__":
    cfg = load_config()
    print(json.dumps({k: str(v) if v else None for k, v in cfg.items()}, ensure_ascii=False, indent=2))
