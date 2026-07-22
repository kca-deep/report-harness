"""hwpx 구조 검증 + md↔되읽기 왕복 대조 (spec §6-4, AI 티 3중장치-③). stdlib-only."""
import sys, json, re, zipfile, xml.etree.ElementTree as ET

NUM = re.compile(r"\d+(?:[.,]\d+)*")
# 개조식 항목 선두 합법 기호 (lint_md_profile.LEAD와 동일 어휘) — 잔재 검사 전에 벗겨낸다.
LEAD = re.compile(r"^\s*(□|ㅇ|○|-|※|＊|\d+\.|\[\d+\])\s")
HEADING = re.compile(r"^#{1,6}\s")
HR = re.compile(r"^-{3,}$")
STRIKE = re.compile(r"~~[^~\n]+~~")
ITALIC = re.compile(r"(?<!\*)\*(?!\*)[^*\n]+(?<!\*)\*(?!\*)")
INLINE_DASH = re.compile(r"\s-\s")

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

def normalize_num(s):
    """콤마 제거 + 소수 끝자리 0 제거. float 변환 불가하면 원문 그대로(비교 실패로 손실 검출)."""
    t = s.replace(",", "")
    try:
        float(t)
    except ValueError:
        return s
    if "." in t:
        t = t.rstrip("0")
        if t.endswith("."):
            t = t[:-1]
    return t

def has_markdown_leftover(line):
    stripped = line.strip()
    if not stripped:
        return False
    if HR.match(stripped):
        return True
    if HEADING.match(stripped):
        return True
    body = LEAD.sub("", line, count=1)  # 항목 선두 합법 기호(-, ㅇ 등)는 잔재 판정에서 제외
    if "`" in body:
        return True
    if "**" in body:
        return True
    if STRIKE.search(body):
        return True
    if ITALIC.search(body):
        return True
    if INLINE_DASH.search(body):
        return True
    return False

def compare_texts(src, rt):
    a, b = profile_counts(src), profile_counts(rt)
    issues = []
    for k in ("sections", "points", "subs", "footnotes", "tables", "max_cols"):
        if a[k] != b[k]:
            issues.append({"rule": f"count-mismatch:{k}", "src": a[k], "roundtrip": b[k]})
    a_num = {normalize_num(n) for n in a["numbers"]}
    b_num = {normalize_num(n) for n in b["numbers"]}
    lost = a_num - b_num
    if lost:
        issues.append({"rule": "numbers-lost", "values": sorted(lost)[:20]})
    for i, line in enumerate(rt.splitlines(), 1):
        if not line.strip().startswith("|") and has_markdown_leftover(line):
            issues.append({"rule": "markdown-leftover", "line": i, "text": line.strip()[:80]})
    return issues

USAGE = "usage: validate_hwpx.py structural <path.hwpx> | validate_hwpx.py compare <src.md> <rt.md>"

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        if mode == "structural":
            if len(sys.argv) < 3:
                raise IndexError
            errs = structural_check(sys.argv[2])
            print(json.dumps({"errors": errs}, ensure_ascii=False))
            sys.exit(1 if errs else 0)
        elif mode == "compare":
            if len(sys.argv) < 4:
                raise IndexError
            src = open(sys.argv[2], encoding="utf-8").read()
            rt = open(sys.argv[3], encoding="utf-8").read()
            issues = compare_texts(src, rt)
            print(json.dumps({"issues": issues}, ensure_ascii=False, indent=1))
            sys.exit(1 if issues else 0)
        else:
            print(USAGE, file=sys.stderr)
            sys.exit(2)
    except IndexError:
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)
