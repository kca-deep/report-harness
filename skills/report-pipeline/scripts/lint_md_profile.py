"""md-profile 결정론 린트 (spec §6 4단방어-①, AI 티 3중장치-①). stdlib-only.
개조식 기호(□ㅇ○-※＊)는 항목 '선두'에서만 합법. 그 외 위치의 마크다운 기호는 위반."""
import sys, json, re

LEAD = re.compile(r"^\s*(□|ㅇ|○|-|※|＊|\d+\.|\[\d+\])\s")   # 항목 선두 허용 기호 (반각 * 제외 — 각주는 전각 ＊만 합법)
HIGHLIGHT_TOKEN = re.compile(r"==")  # `==특히 강조==` 하이라이트 마커(R040) — 짝수 개만 합법
TABLE = re.compile(r"^\s*\|")
BOLD = re.compile(r"\*\*[^*\n]+\*\*")
INLINE_BAD = re.compile(r"(?:\s-\s|(?<!\*)\*(?!\*)|`|^#{1,6}\s|\s>\s)")
NON_BOLD = re.compile(r"(?<!\*)\*(?!\*)[^*\n]+(?<!\*)\*(?!\*)|~~[^~\n]+~~")
TRIPLE_STAR = re.compile(r"\*{3,}")
# 실제 HTML 태그명 화이트리스트만 검출 — <AI 활용 방안> 같은 꺾쇠 라벨은 코퍼스 관례상 통과
HTML = re.compile(
    r"(?i)</?(br|div|span|table|thead|tbody|tr|td|th|img|em|strong|"
    r"hr|ul|ol|li|sub|sup|font|center|h[1-6])\b[^>]*>"
)

def lint_text(text):
    out, bullet_run = [], 0
    depth_base = None  # 현재 ㅇ/○/□ 블록에서 첫 대시의 들여쓰기(최상위 기준선)
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        # `==` 하이라이트 마커(R040)는 한 줄 안에서 짝이 맞아야 한다 — 홀수면 잔존 위험
        if len(HIGHLIGHT_TOKEN.findall(line)) % 2 == 1:
            out.append({"line": i, "rule": "highlight-unpaired", "text": line.strip()[:80]})
        if TABLE.match(line):
            cols = len([c for c in line.strip().strip("|").split("|")])
            if cols > 6 and not set(line.strip()) <= set("|- :"):
                out.append({"line": i, "rule": "table-too-wide", "text": line.strip()[:80]})
            continue
        if HTML.search(line):
            out.append({"line": i, "rule": "html-tag", "text": line.strip()[:80]})
        stripped = line.strip()
        # 문장 중간(항목 선두가 아닌 위치)의 □ 검출.
        # ※는 인라인 후행 참조가 코퍼스 합법 관례이므로 제외, ㅇ은 오탐 위험으로 이번 범위 제외.
        # 선두 □가 합법인 줄에서도 같은 줄의 두 번째 □는 검출.
        if stripped.count("□") > (1 if stripped.startswith("□") else 0):
            out.append({"line": i, "rule": "misplaced-marker", "text": stripped[:80]})
        if stripped.startswith("ㅇ") or stripped.startswith("○") or stripped.startswith("□"):
            bullet_run = 0
            depth_base = None
        elif stripped.startswith("-"):
            leading_spaces = len(line) - len(line.lstrip())
            if depth_base is None:
                depth_base = leading_spaces
            if leading_spaces > depth_base:
                # 대시는 중첩 불가 — 기준선보다 더 들여쓴 대시는 깊이 초과 (4단은 ※/＊)
                out.append({"line": i, "rule": "depth-exceeded", "text": stripped[:80]})
            else:
                if leading_spaces < depth_base:
                    depth_base = leading_spaces
                bullet_run += 1
                # R045: 상위 계층 하나에 딸리는 하위 계층은 최대 2개 — 3개째부터 위반.
                # 초과분은 개수를 쳐내지 말고 성격이 가까운 항목끼리 통합 서술로 합친다.
                if bullet_run == 3:
                    out.append({"line": i, "rule": "bullet-overflow", "text": stripped[:80]})
        if TRIPLE_STAR.search(line):
            out.append({"line": i, "rule": "non-bold-markup", "text": stripped[:80]})
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
