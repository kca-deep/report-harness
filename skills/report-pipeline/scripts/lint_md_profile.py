"""md-profile 결정론 린트 (spec §6 4단방어-①, AI 티 3중장치-①). stdlib-only.
개조식 기호(□ㅇ○-※＊)는 항목 '선두'에서만 합법. 그 외 위치의 마크다운 기호는 위반."""
import sys, json, re

LEAD = re.compile(r"^\s*(□|ㅇ|○|-|※|＊|\*|\d+\.|\[\d+\])\s")   # 항목 선두 허용 기호
TABLE = re.compile(r"^\s*\|")
BOLD = re.compile(r"\*\*[^*\n]+\*\*")
INLINE_BAD = re.compile(r"(?:\s-\s|(?<!\*)\*(?!\*)|`|^#{1,6}\s|\s>\s)")
NON_BOLD = re.compile(r"(?<!\*)\*(?!\*)[^*\n]+(?<!\*)\*(?!\*)|~~[^~\n]+~~")
HTML = re.compile(r"</?[a-zA-Z][^>]*>")

def lint_text(text):
    out, bullet_run = [], 0
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if TABLE.match(line):
            cols = len([c for c in line.strip().strip("|").split("|")])
            if cols > 6 and not set(line.strip()) <= set("|- :"):
                out.append({"line": i, "rule": "table-too-wide", "text": line.strip()[:80]})
            continue
        if HTML.search(line):
            out.append({"line": i, "rule": "html-tag", "text": line.strip()[:80]})
        stripped = line.strip()
        if stripped.startswith("ㅇ") or stripped.startswith("○"):
            bullet_run = 0
        elif stripped.startswith("-"):
            bullet_run += 1
            if bullet_run == 6:
                out.append({"line": i, "rule": "bullet-overflow", "text": stripped[:80]})
            # 선행 공백이 5칸 이상이면 깊이 초과 (4단 위계 초과)
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces >= 5:
                out.append({"line": i, "rule": "depth-exceeded", "text": stripped[:80]})
        body = LEAD.sub("", line, count=1)
        body_nobold = BOLD.sub("", body)
        if NON_BOLD.search(body_nobold):
            out.append({"line": i, "rule": "non-bold-markup", "text": stripped[:80]})
        if INLINE_BAD.search(body_nobold):
            out.append({"line": i, "rule": "inline-markdown", "text": stripped[:80]})
    return out

if __name__ == "__main__":
    text = open(sys.argv[1], encoding="utf-8").read()
    v = lint_text(text)
    print(json.dumps({"violations": v}, ensure_ascii=False, indent=1))
    sys.exit(1 if v else 0)
