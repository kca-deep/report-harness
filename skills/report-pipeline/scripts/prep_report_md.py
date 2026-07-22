"""변환 전 정규화 — 내용 무손실 보장 (spec §6 '작성된 md 그대로'). stdlib-only."""
import sys, re, hashlib, argparse

COMMENT = re.compile(r"<!--.*?-->", re.S)
HR_LINE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
FOOT = re.compile(r"^(\s*)\\?\*\s(?=\S)")   # 라인 선두 각주 마커 → ＊

def prep(text):
    text = COMMENT.sub("", text)
    lines = []
    for line in text.splitlines():
        if HR_LINE.match(line):
            continue                          # 라인만 제거 — 주변 빈 줄은 건드리지 않음
        lines.append(FOOT.sub(r"\1＊ ", line))
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")

def content_fingerprint(text):
    t = COMMENT.sub("", text)
    t = "\n".join(l for l in t.splitlines() if not HR_LINE.match(l))
    t = re.sub(r"[＊*\\]", "", t)            # 각주 마커 표기 차이 무시
    t = re.sub(r"\s+", " ", t).strip()
    return hashlib.sha256(t.encode()).hexdigest()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("-o", required=True)
    a = ap.parse_args()
    src = open(a.src, encoding="utf-8").read()
    out = prep(src)
    if content_fingerprint(src) != content_fingerprint(out):
        print("FATAL: content fingerprint mismatch — 무손실 위반", file=sys.stderr)
        sys.exit(2)
    open(a.o, "w", encoding="utf-8").write(out)
    print(f"OK {a.o}")
