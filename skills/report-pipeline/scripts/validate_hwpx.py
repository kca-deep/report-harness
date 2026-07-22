"""hwpx 구조 검증 + md↔되읽기 왕복 대조 (spec §6-4, AI 티 3중장치-③). stdlib-only."""
import sys, json, re, zipfile, xml.etree.ElementTree as ET

NUM = re.compile(r"\d+(?:[.,]\d+)*")
LEFTOVER = re.compile(r"\*\*|(?<!\S)[#>`](?!\S)|\s-\s")

def structural_check(path):
    errs = []
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                errs.append(f"zip corrupt: {bad}")
            for n in z.namelist():
                if n.endswith(".xml"):
                    try:
                        ET.fromstring(z.read(n))
                    except ET.ParseError as e:
                        errs.append(f"{n}: {e}")
    except (zipfile.BadZipFile, FileNotFoundError) as e:
        errs.append(str(e))
    return errs

def profile_counts(text):
    lines = text.splitlines()
    tbl_rows = [l for l in lines if l.strip().startswith("|")]
    tables = 0
    prev = False
    for l in lines:
        cur = l.strip().startswith("|")
        if cur and not prev:
            tables += 1
        prev = cur
    return {
        "sections": sum(l.strip().startswith("□") for l in lines),
        "points": sum(l.strip()[:1] in ("ㅇ", "○") for l in lines),
        "subs": sum(l.strip().startswith("-") and not set(l.strip()) <= set("|- :") for l in lines if not l.strip().startswith("|")),
        "footnotes": sum(l.strip().startswith("＊") for l in lines),
        "tables": tables,
        "max_cols": max([len(r.strip().strip("|").split("|")) for r in tbl_rows], default=0),
        "numbers": set(NUM.findall(text)),
    }

def compare_texts(src, rt):
    a, b = profile_counts(src), profile_counts(rt)
    issues = []
    for k in ("sections", "points", "subs", "footnotes", "tables"):
        if a[k] != b[k]:
            issues.append({"rule": f"count-mismatch:{k}", "src": a[k], "roundtrip": b[k]})
    lost = a["numbers"] - b["numbers"]
    if lost:
        issues.append({"rule": "numbers-lost", "values": sorted(lost)[:20]})
    for i, line in enumerate(rt.splitlines(), 1):
        if not line.strip().startswith("|") and LEFTOVER.search(line):
            issues.append({"rule": "markdown-leftover", "line": i, "text": line.strip()[:80]})
    return issues

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "structural":
        errs = structural_check(sys.argv[2])
        print(json.dumps({"errors": errs}, ensure_ascii=False))
        sys.exit(1 if errs else 0)
    if mode == "compare":
        src = open(sys.argv[2], encoding="utf-8").read()
        rt = open(sys.argv[3], encoding="utf-8").read()
        issues = compare_texts(src, rt)
        print(json.dumps({"issues": issues}, ensure_ascii=False, indent=1))
        sys.exit(1 if issues else 0)
    sys.exit(2)
