"""패키징 PII 가드 (spec §12). 전화·이메일 잔존 시 배포 차단."""
import sys, re, pathlib

PHONE = re.compile(r"(?<!\d)0\d{1,2}[-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

def scan_dir(root):
    hits = []
    for p in pathlib.Path(root).rglob("*"):
        if p.suffix.lower() in {".md", ".json", ".txt", ".py", ".csv", ".jsonl", ".yml", ".yaml"} and p.is_file():
            t = p.read_text(encoding="utf-8", errors="ignore")
            for rx, kind in ((PHONE, "phone"), (EMAIL, "email")):
                for m in rx.findall(t):
                    hits.append({"file": str(p), "kind": kind, "value": m})
    return hits

if __name__ == "__main__":
    hits = scan_dir(sys.argv[1])
    for h in hits:
        print(f"PII {h['kind']}: {h['file']}: {h['value']}")
    sys.exit(1 if hits else 0)
