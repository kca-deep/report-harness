#!/usr/bin/env python3
"""kordoc generate_document 산출 hwpx를 양식 정합으로 후처리한다 (stdlib-only).

기능:
  --star-footnote  ＊ 시작 문단의 run charPrIDRef를 참고 스타일(header.xml에서
                    height=1300·fontRef=맑은고딕 계열)로 치환한다. kordoc은 ※만
                    참고 스타일로 인식하고 전각 ＊는 본문 스타일로 남는 결함의 후처리
                    (기존 수동 zip 패치의 스크립트화, R011).
  --spacing         계층 전환 지점(발신줄→□/□→ㅇ/ㅇ→-/-→＊/＊→표캡션/블록 구분)의
                    간격을 원본 KCA 양식 실측값(스페이서 문단 방식)으로 재현한다.
                    전환 지점에 이미 빈 문단이 있으면 그 charPr 높이를 치환하고,
                    없으면 새 스페이서 문단을 삽입한다. 같은 묶음으로 표 셀 텍스트
                    가운데 정렬·표 유닛 앞뒤 간격 보정·제목 박스 테두리 제거,
                    제목 박스 상단 여백 제거(앵커 줄간격 100%·outMargin top 0 — 상단
                    그라데이션 밴드 행은 양식 원형이므로 유지, R022)·표 캡션/셀
                    12pt(R023)·□ 절 제목 볼드(R024)·☞ 계층 띄어쓰기(R025)도 적용한다.
  --sender-size N   발신 줄(classify=="sending") 문단 run들의 charPr을 폰트는 유지한 채
                    높이만 N(pt)로 치환한다. --all에는 포함되지 않는다(값 필요, 별도 지정).
  --star-indent L,I ＊·※ 문단의 paraPr margin을 left=L(pt)·intent=I(pt, 음수 허용)로
                    치환한다(prev/next 여백은 유지). --all에는 포함되지 않는다.
  --all             --star-footnote·--spacing을 적용.

실측 근거: /Users/bcchung81/workspace/claudian/reports/20260722/1313_하네스-AI성과-관리체계/
research/fetched/양식-문단간격/추출결과.md — 계층 간격은 paraPr 위/아래 간격이 아니라
글자크기를 줄인 빈 스페이서 문단으로 구현된다(문단모양 자체 간격 필드는 전부 0).
"""
import sys, json, re, copy, zipfile, pathlib, tempfile, os
import xml.etree.ElementTree as ET

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
}
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)

SECTION_RE = re.compile(r"^Contents/section\d+\.xml$")
SENDING_RE = re.compile(r"^<\s*'?\d")  # "< '26. 7. 22.(수), ... >" 형 발신 줄
CAPTION_RE = re.compile(r"^[\[<]")     # "[ 표 제목 ]" / "< 표 제목 >" 형 캡션
DAE, STAR, CHAM, DASH, ARROW = "□", "＊", "※", "-", "☞"
YO_CHARS = ("ㅇ", "○")

# 전환 유형 → (이름, 스페이서 charPr 높이 HWPUNIT = pt*100)
TRANSITIONS = {
    ("sending", "dae"): ("sending_to_dae", 800),
    ("dae", "yo"): ("dae_to_yo", 600),
    ("yo", "yo"): ("yo_to_yo", 600),            # 연속 ㅇ 문단 사이 (사용자 확정)
    ("dash", "yo"): ("dash_to_yo", 600),        # 하위 대시에서 다음 ㅇ 복귀
    ("yo", "dash"): ("yo_to_dash", 600),
    ("dash", "star"): ("dash_to_star", 300),
    ("yo", "star"): ("yo_to_star", 300),        # 양식 미실측 전환 — dash→star 3pt 유추 적용
    ("star", "caption"): ("star_to_caption", 1000),
    ("caption", "table"): ("caption_to_table", 300),   # 캡션→표 3pt(사용자 확정 '26.7.22)
    ("table", "cham"): ("table_to_cham", 300),         # 표→※ 3pt
    ("yo", "caption"): ("yo_to_caption", 600),         # 문단→캡션 6pt
    ("dash", "caption"): ("dash_to_caption", 600),
    ("cham", "caption"): ("cham_to_caption", 600),
    # ☞ 결론 유도 기호(R025) — ※·＊ 인접 간격(3pt) 준용
    ("cham", "arrow"): ("cham_to_arrow", 300),
    ("star", "arrow"): ("star_to_arrow", 300),
    ("yo", "arrow"): ("yo_to_arrow", 300),
    ("dash", "arrow"): ("dash_to_arrow", 300),
    ("table", "arrow"): ("table_to_arrow", 300),
}
BLOCK_BOUNDARY_HEIGHT = 1500  # 직전 블록 끝 → 새 □ (일반 빈줄)


class PostprocessError(Exception):
    """치명적 후처리 오류(참고 스타일 미발견 등) — exit 2 대상."""


def qn(prefix, local):
    return f"{{{NS[prefix]}}}{local}"


# ---------------------------------------------------------------------------
# 문단 판독
# ---------------------------------------------------------------------------

def para_text(p):
    """문단 직속 hp:run들의 hp:t 텍스트를 이어붙인다(중첩 표 셀 내부는 별도 문단이므로 무관)."""
    texts = []
    for run in p.findall(qn("hp", "run")):
        t = run.find(qn("hp", "t"))
        if t is not None and t.text:
            texts.append(t.text)
    return "".join(texts)


def para_has_table(p):
    for run in p.findall(qn("hp", "run")):
        if run.find(qn("hp", "tbl")) is not None:
            return True
    return False


def classify(p):
    """문단 선두 기호로 계층 유형을 판정한다."""
    if para_has_table(p):
        return "table"
    text = para_text(p).strip()
    if not text:
        return "empty"
    if text.startswith(DAE):
        return "dae"
    if text[0] in YO_CHARS:
        return "yo"
    if text.startswith(STAR):
        return "star"
    if text.startswith(CHAM):
        return "cham"
    if text.startswith(ARROW):
        return "arrow"
    if SENDING_RE.match(text):
        return "sending"
    if CAPTION_RE.match(text):
        return "caption"
    if text.startswith(DASH):
        return "dash"
    return "other"


def transition_for(prev_kind, next_kind):
    if prev_kind is None or next_kind is None:
        return None
    key = (prev_kind, next_kind)
    if key in TRANSITIONS:
        return TRANSITIONS[key]
    if next_kind == "dae" and prev_kind != "sending":
        return ("block_boundary", BLOCK_BOUNDARY_HEIGHT)
    return None


# ---------------------------------------------------------------------------
# ＊ 각주 charPr 치환
# ---------------------------------------------------------------------------

def _hangul_fontfaces(header_root):
    """{font id: face} — 최초(HANGUL) lang 테이블만 사용(전 lang 동일 face 목록)."""
    fonts = {}
    for ff in header_root.iter(qn("hh", "fontface")):
        for f in ff.findall(qn("hh", "font")):
            fonts.setdefault(f.get("id"), f.get("face"))
        break
    return fonts


def find_ref_charpr_id(header_root):
    """height=1300·fontRef=맑은고딕(공백 없는 표기 우선) charPr id를 탐색한다."""
    fonts = _hangul_fontfaces(header_root)
    fallback = None
    for cp in header_root.iter(qn("hh", "charPr")):
        if cp.get("height") != "1300":
            continue
        fr = cp.find(qn("hh", "fontRef"))
        if fr is None:
            continue
        face = fonts.get(fr.get("hangul"), "")
        if face == "맑은고딕":
            return cp.get("id")
        if fallback is None and "맑은고딕" in face.replace(" ", ""):
            fallback = cp.get("id")
    return fallback


def apply_star_footnote(header_root, section_roots):
    ref_id = find_ref_charpr_id(header_root)
    if ref_id is None:
        raise PostprocessError(
            "참고 charPr(header.xml height=1300·fontRef=맑은고딕 계열)을 찾지 못했습니다"
        )
    stars_found = 0
    runs_changed = 0
    for sec_root in section_roots:
        for p in sec_root.iter(qn("hp", "p")):
            if not para_text(p).strip().startswith(STAR):
                continue
            stars_found += 1
            for run in p.findall(qn("hp", "run")):
                if run.get("charPrIDRef") != ref_id:
                    run.set("charPrIDRef", ref_id)
                    runs_changed += 1
    return {"ref_charpr_id": ref_id, "stars_found": stars_found, "runs_changed": runs_changed}


# ---------------------------------------------------------------------------
# 계층 간격 스페이서
# ---------------------------------------------------------------------------

def ensure_charpr_height(header_root, height):
    """height(HWPUNIT)와 일치하는 charPr id를 재사용하거나, 없으면 id0을 복제해 새로 등록한다."""
    height_s = str(height)
    charprops = header_root.find(f".//{qn('hh', 'charProperties')}")
    for cp in charprops.findall(qn("hh", "charPr")):
        if cp.get("height") == height_s:
            return cp.get("id")
    template = charprops.find(qn("hh", "charPr"))
    new_cp = copy.deepcopy(template)
    max_id = max(int(cp.get("id")) for cp in charprops.findall(qn("hh", "charPr")))
    new_id = str(max_id + 1)
    new_cp.set("id", new_id)
    new_cp.set("height", height_s)
    charprops.append(new_cp)
    charprops.set("itemCnt", str(int(charprops.get("itemCnt", "0")) + 1))
    return new_id


def ensure_neutral_parapr(header_root):
    """margin.prev=margin.next=0인 paraPr id를 재사용하거나, 없으면 새로 등록한다.
    (스페이서 문단은 문단 자체 간격이 아니라 글자크기로만 간격을 내야 하므로 margin은 0이어야 한다.)"""
    paraprops = header_root.find(f".//{qn('hh', 'paraProperties')}")
    for pp in paraprops.findall(qn("hh", "paraPr")):
        margin = pp.find(qn("hh", "margin"))
        if margin is None:
            continue
        prev = margin.find(qn("hc", "prev"))
        nxt = margin.find(qn("hc", "next"))
        if prev is not None and nxt is not None and prev.get("value") == "0" and nxt.get("value") == "0":
            return pp.get("id")
    template = paraprops.find(qn("hh", "paraPr"))
    new_pp = copy.deepcopy(template)
    max_id = max(int(pp.get("id")) for pp in paraprops.findall(qn("hh", "paraPr")))
    new_id = str(max_id + 1)
    new_pp.set("id", new_id)
    margin = new_pp.find(qn("hh", "margin"))
    if margin is not None:
        for tag in ("intent", "left", "right", "prev", "next"):
            el = margin.find(qn("hc", tag))
            if el is not None:
                el.set("value", "0")
    paraprops.append(new_pp)
    paraprops.set("itemCnt", str(int(paraprops.get("itemCnt", "0")) + 1))
    return new_id


def make_spacer_paragraph(parapr_id, charpr_id):
    p = ET.Element(qn("hp", "p"), {"paraPrIDRef": parapr_id, "styleIDRef": "0"})
    run = ET.SubElement(p, qn("hp", "run"), {"charPrIDRef": charpr_id})
    ET.SubElement(run, qn("hp", "t"))
    return p


def apply_spacing_section(header_root, sec_root):
    """sec_root(hs:sec)의 최상위 hp:p 시퀀스를 훑어 전환 지점마다 스페이서를 적용한다.
    반환: 적용 이벤트 목록({"type": "insert"|"modify", "transition": ..., "height": ...})."""
    p_tag = qn("hp", "p")
    children = list(sec_root)
    kinds = [classify(c) if c.tag == p_tag else None for c in children]
    n = len(children)
    out = []
    events = []
    prev_content_kind = None
    for i, child in enumerate(children):
        if child.tag != p_tag:
            out.append(child)
            continue
        kind = kinds[i]
        if kind == "empty":
            next_kind = None
            for j in range(i + 1, n):
                if children[j].tag == p_tag and kinds[j] != "empty":
                    next_kind = kinds[j]
                    break
            trans = transition_for(prev_content_kind, next_kind)
            if trans:
                name, height = trans
                cp_id = ensure_charpr_height(header_root, height)
                run = child.find(qn("hp", "run"))
                if run is not None:
                    run.set("charPrIDRef", cp_id)
                events.append({"type": "modify", "transition": name, "height": height})
            out.append(child)
            continue
        prev_item_is_empty = i > 0 and kinds[i - 1] == "empty"
        if prev_content_kind is not None and not prev_item_is_empty:
            trans = transition_for(prev_content_kind, kind)
            if trans:
                name, height = trans
                cp_id = ensure_charpr_height(header_root, height)
                pp_id = ensure_neutral_parapr(header_root)
                out.append(make_spacer_paragraph(pp_id, cp_id))
                events.append({"type": "insert", "transition": name, "height": height})
        out.append(child)
        prev_content_kind = kind
    sec_root[:] = out
    return events


def apply_spacing(header_root, section_roots):
    events = []
    for sec_root in section_roots:
        events.extend(apply_spacing_section(header_root, sec_root))
    return {"events": events, "inserted": sum(1 for e in events if e["type"] == "insert"),
            "modified": sum(1 for e in events if e["type"] == "modify")}


def ensure_centered_clone(header_root, base_id, cache):
    """base paraPr을 복제해 align horizontal=CENTER인 paraPr id를 반환(중복 생성 방지 캐시)."""
    if base_id in cache:
        return cache[base_id]
    paraprops = header_root.find(f".//{qn('hh', 'paraProperties')}")
    base = None
    for pp in paraprops.findall(qn("hh", "paraPr")):
        if pp.get("id") == base_id:
            base = pp
            break
    if base is None:
        return base_id
    align = base.find(qn("hh", "align"))
    if align is not None and align.get("horizontal") == "CENTER":
        cache[base_id] = base_id
        return base_id
    new_pp = copy.deepcopy(base)
    max_id = max(int(pp.get("id")) for pp in paraprops.findall(qn("hh", "paraPr")))
    new_id = str(max_id + 1)
    new_pp.set("id", new_id)
    na = new_pp.find(qn("hh", "align"))
    if na is not None:
        na.set("horizontal", "CENTER")
    paraprops.append(new_pp)
    paraprops.set("itemCnt", str(len(paraprops.findall(qn("hh", "paraPr")))))
    cache[base_id] = new_id
    return new_id


def apply_center_tables(header_root, section_roots):
    """표 캡션 문단과 표 래퍼 문단(treatAsChar 표)을 가운데 정렬 paraPr로 교체."""
    p_tag = qn("hp", "p")
    cache = {}
    centered = {"caption": 0, "table": 0}
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag:
                continue
            kind = classify(child)
            if kind not in ("caption", "table"):
                continue
            base_id = child.get("paraPrIDRef")
            if base_id is None:
                continue
            new_id = ensure_centered_clone(header_root, base_id, cache)
            if new_id != base_id:
                child.set("paraPrIDRef", new_id)
            centered[kind] += 1
    return {"centered": centered, "new_parapr": {k: v for k, v in cache.items() if k != v}}


def _iter_content_tables(section_roots):
    """(hp:tbl 요소, is_title_box) 쌍을 문서 순서대로 생성한다.
    첫 □ 문단 이전에 나오는 표는 제목 박스(is_title_box=True)로 판정한다."""
    p_tag = qn("hp", "p")
    seen_dae = False
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag:
                continue
            kind = classify(child)
            if kind == "dae":
                seen_dae = True
                continue
            if kind != "table":
                continue
            for run in child.findall(qn("hp", "run")):
                tbl = run.find(qn("hp", "tbl"))
                if tbl is not None:
                    yield tbl, not seen_dae


def apply_center_cell_text(header_root, section_roots):
    """본문 콘텐츠 표(제목 박스 제외)의 hp:tbl 내부 subList 문단 전부를 가운데 정렬한다."""
    p_tag = qn("hp", "p")
    cache = {}
    tables = 0
    paragraphs = 0
    for tbl, is_title in _iter_content_tables(section_roots):
        if is_title:
            continue
        tables += 1
        for cell_p in tbl.iter(p_tag):
            base_id = cell_p.get("paraPrIDRef")
            if base_id is None:
                continue
            new_id = ensure_centered_clone(header_root, base_id, cache)
            if new_id != base_id:
                cell_p.set("paraPrIDRef", new_id)
            paragraphs += 1
    return {"tables": tables, "paragraphs": paragraphs}


BORDER_TAGS = ("leftBorder", "rightBorder", "topBorder", "bottomBorder")


def ensure_borderless_fill(header_root):
    """4변 전부 type=NONE인 borderFill id를 재사용하거나, 없으면 첫 borderFill을
    복제해 leftBorder/rightBorder/topBorder/bottomBorder만 NONE으로 바꿔 등록한다
    (slash/backSlash 대각선은 건드리지 않는다)."""
    borderfills = header_root.find(f".//{qn('hh', 'borderFills')}")
    for bf in borderfills.findall(qn("hh", "borderFill")):
        if all((el := bf.find(qn("hh", t))) is not None and el.get("type") == "NONE"
               for t in BORDER_TAGS):
            return bf.get("id")
    template = borderfills.find(qn("hh", "borderFill"))
    new_bf = copy.deepcopy(template)
    max_id = max(int(bf.get("id")) for bf in borderfills.findall(qn("hh", "borderFill")))
    new_id = str(max_id + 1)
    new_bf.set("id", new_id)
    for t in BORDER_TAGS:
        el = new_bf.find(qn("hh", t))
        if el is not None:
            el.set("type", "NONE")
    borderfills.append(new_bf)
    borderfills.set("itemCnt", str(int(borderfills.get("itemCnt", "0")) + 1))
    return new_id


def ensure_borderless_variant(header_root, base_id, cache):
    """base_id borderFill의 배경(fillBrush·그라데이션)은 보존하고 4변 테두리만
    NONE으로 바꾼 변형 id를 반환한다 — hwpx는 테두리·배경이 borderFill 한 엔티티라
    통째 교체 시 배경이 소실되므로, 원본별 무테두리 변형을 복제 생성한다."""
    if base_id in cache:
        return cache[base_id]
    borderfills = header_root.find(f".//{qn('hh', 'borderFills')}")
    base = None
    for bf in borderfills.findall(qn("hh", "borderFill")):
        if bf.get("id") == base_id:
            base = bf
            break
    if base is None:
        cache[base_id] = base_id
        return base_id
    if all((el := base.find(qn("hh", t))) is not None and el.get("type") == "NONE"
           for t in BORDER_TAGS):
        cache[base_id] = base_id
        return base_id
    new_bf = copy.deepcopy(base)
    max_id = max(int(bf.get("id")) for bf in borderfills.findall(qn("hh", "borderFill")))
    new_id = str(max_id + 1)
    new_bf.set("id", new_id)
    for t in BORDER_TAGS:
        el = new_bf.find(qn("hh", t))
        if el is not None:
            el.set("type", "NONE")
    borderfills.append(new_bf)
    borderfills.set("itemCnt", str(int(borderfills.get("itemCnt", "0")) + 1))
    cache[base_id] = new_id
    return new_id


def apply_title_box_borderless(header_root, section_roots):
    """제목 박스(첫 □ 이전 표)의 hp:tbl·hp:tc 등 borderFillIDRef를 '원본 배경 보존 +
    테두리만 NONE' 변형으로 교체한다(그라데이션 등 fillBrush 유지)."""
    title_tables = [tbl for tbl, is_title in _iter_content_tables(section_roots) if is_title]
    if not title_tables:
        return {"found": False, "fills_replaced": 0}
    cache = {}
    replaced = 0
    for tbl in title_tables:
        for el in tbl.iter():
            ref = el.get("borderFillIDRef")
            if ref is None:
                continue
            new_ref = ensure_borderless_variant(header_root, ref, cache)
            if new_ref != ref:
                el.set("borderFillIDRef", new_ref)
                replaced += 1
    return {"found": True, "fills_replaced": replaced,
            "variants": {k: v for k, v in cache.items() if k != v}}


def ensure_linespacing_parapr(header_root, base_id, percent, cache):
    """base_id paraPr의 lineSpacing value만 percent로 바꾼 복제본 id를 반환한다."""
    key = (base_id, percent)
    if key in cache:
        return cache[key]
    paraprops = header_root.find(f".//{qn('hh', 'paraProperties')}")
    base = None
    for pp in paraprops.findall(qn("hh", "paraPr")):
        if pp.get("id") == base_id:
            base = pp
            break
    if base is None:
        cache[key] = base_id
        return base_id
    ls = base.find(qn("hh", "lineSpacing"))
    if ls is not None and ls.get("value") == str(percent):
        cache[key] = base_id
        return base_id
    new_pp = copy.deepcopy(base)
    max_id = max(int(pp.get("id")) for pp in paraprops.findall(qn("hh", "paraPr")))
    new_id = str(max_id + 1)
    new_pp.set("id", new_id)
    nls = new_pp.find(qn("hh", "lineSpacing"))
    if nls is not None:
        nls.set("value", str(percent))
    paraprops.append(new_pp)
    paraprops.set("itemCnt", str(len(paraprops.findall(qn("hh", "paraPr")))))
    cache[key] = new_id
    return new_id


def apply_title_box_topgap(header_root, section_roots):
    """제목 박스(첫 □ 이전 표) 위 여백을 제거한다(R022 개정 '26.7.24 — 행 삭제 금지).
    양식 실측(20260722건): 제목표는 3행 원형이고 상단 얇은 행(3.8pt)은 그라데이션 배경
    밴드이므로 유지해야 한다. 여백의 실원인은 앵커 문단(treatAsChar 표를 담은 문단)의
    줄간격 160%가 표 높이의 60%를 여백으로 벌리는 것 — 앵커 문단 줄간격을 100%로 치환하고
    표 outMargin top을 0으로 조인다."""
    p_tag = qn("hp", "p")
    cache = {}
    anchors_fixed = 0
    outmargins_fixed = 0
    title_ids = set()
    for tbl, is_title in _iter_content_tables(section_roots):
        if not is_title:
            continue
        title_ids.add(id(tbl))
        out = tbl.find(qn("hp", "outMargin"))
        if out is not None and out.get("top") not in (None, "0"):
            out.set("top", "0")
            outmargins_fixed += 1
    if not title_ids:
        return {"anchors_fixed": 0, "outmargins_fixed": 0}
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag:
                continue
            has_title = any(
                id(tbl) in title_ids
                for run in child.findall(qn("hp", "run"))
                for tbl in run.findall(qn("hp", "tbl"))
            )
            if not has_title:
                continue
            base_id = child.get("paraPrIDRef")
            if base_id is None:
                continue
            new_id = ensure_linespacing_parapr(header_root, base_id, 100, cache)
            if new_id != base_id:
                child.set("paraPrIDRef", new_id)
                anchors_fixed += 1
    return {"anchors_fixed": anchors_fixed, "outmargins_fixed": outmargins_fixed}


BANNER_LABEL_RE = re.compile(r"^(붙\s*임\s*\d*|참고\s*\d*)$")


def _is_banner_table(tbl):
    """붙임·참고 배너 표(1행 3열, 첫 셀이 '붙 임'/'붙임 N'/'참고N') 판정 (R009·R027)."""
    rows = tbl.findall(qn("hp", "tr"))
    if len(rows) != 1:
        return False
    cells = rows[0].findall(qn("hp", "tc"))
    if len(cells) != 3:
        return False
    first_texts = [t.text or "" for t in cells[0].iter(qn("hp", "t"))]
    return bool(BANNER_LABEL_RE.match("".join(first_texts).strip()))


def apply_caption_table_font(header_root, section_roots, pt=12):
    """표 캡션 문단과 본문 콘텐츠 표(제목 박스·붙임/참고 배너 제외) 셀 문단의 charPr 크기를
    pt로 치환한다(R023 — 사용자 확정 '26.7.24). 폰트는 유지하고 높이만 바꾼다."""
    height = int(round(pt * 100))
    p_tag = qn("hp", "p")
    cache = {}
    caption_runs = 0
    cell_runs = 0
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag or classify(child) != "caption":
                continue
            for run in child.findall(qn("hp", "run")):
                base_id = run.get("charPrIDRef")
                if base_id is None:
                    continue
                new_id = ensure_charpr_sized(header_root, base_id, height, cache)
                if new_id != base_id:
                    run.set("charPrIDRef", new_id)
                    caption_runs += 1
    for tbl, is_title in _iter_content_tables(section_roots):
        if is_title or _is_banner_table(tbl):
            continue
        for cell_p in tbl.iter(p_tag):
            for run in cell_p.findall(qn("hp", "run")):
                base_id = run.get("charPrIDRef")
                if base_id is None:
                    continue
                new_id = ensure_charpr_sized(header_root, base_id, height, cache)
                if new_id != base_id:
                    run.set("charPrIDRef", new_id)
                    cell_runs += 1
    return {"height": height, "caption_runs_changed": caption_runs,
            "cell_runs_changed": cell_runs}


def ensure_charpr_font_size(header_root, base_id, face, height, cache):
    """base_id charPr을 전 lang fontRef=face 폰트 id·height로 바꾼 복제본 id를 반환한다."""
    key = (base_id, face, height)
    if key in cache:
        return cache[key]
    fonts = _hangul_fontfaces(header_root)
    font_id = next((fid for fid, f in fonts.items() if f == face), None)
    if font_id is None:
        cache[key] = base_id
        return base_id
    charprops = header_root.find(f".//{qn('hh', 'charProperties')}")
    base = None
    for cp in charprops.findall(qn("hh", "charPr")):
        if cp.get("id") == base_id:
            base = cp
            break
    if base is None:
        cache[key] = base_id
        return base_id
    fr = base.find(qn("hh", "fontRef"))
    if (base.get("height") == str(height) and fr is not None
            and fr.get("hangul") == font_id):
        cache[key] = base_id
        return base_id
    new_cp = copy.deepcopy(base)
    max_id = max(int(cp.get("id")) for cp in charprops.findall(qn("hh", "charPr")))
    new_id = str(max_id + 1)
    new_cp.set("id", new_id)
    new_cp.set("height", str(height))
    nfr = new_cp.find(qn("hh", "fontRef"))
    if nfr is not None:
        for lang in ("hangul", "latin", "hanja", "japanese", "other", "symbol", "user"):
            if nfr.get(lang) is not None:
                nfr.set(lang, font_id)
    charprops.append(new_cp)
    charprops.set("itemCnt", str(int(charprops.get("itemCnt", "0")) + 1))
    cache[key] = new_id
    return new_id


def ensure_pagebreak_parapr(header_root, base_id, cache):
    """base_id paraPr의 breakSetting pageBreakBefore="1" 복제본 id를 반환한다."""
    if base_id in cache:
        return cache[base_id]
    paraprops = header_root.find(f".//{qn('hh', 'paraProperties')}")
    base = None
    for pp in paraprops.findall(qn("hh", "paraPr")):
        if pp.get("id") == base_id:
            base = pp
            break
    if base is None:
        cache[base_id] = base_id
        return base_id
    bs = base.find(qn("hh", "breakSetting"))
    if bs is not None and bs.get("pageBreakBefore") == "1":
        cache[base_id] = base_id
        return base_id
    new_pp = copy.deepcopy(base)
    max_id = max(int(pp.get("id")) for pp in paraprops.findall(qn("hh", "paraPr")))
    new_id = str(max_id + 1)
    new_pp.set("id", new_id)
    nbs = new_pp.find(qn("hh", "breakSetting"))
    if nbs is None:
        nbs = ET.SubElement(new_pp, qn("hh", "breakSetting"))
    nbs.set("pageBreakBefore", "1")
    paraprops.append(new_pp)
    paraprops.set("itemCnt", str(len(paraprops.findall(qn("hh", "paraPr")))))
    cache[base_id] = new_id
    return new_id


def apply_annex_banner(header_root, section_roots):
    """붙임·참고 배너를 양식 참고 블록 정합으로 처리한다(R027 — 사용자 확정 '26.7.24):
    ① 배너 앵커 문단 pageBreakBefore=1 (별도 페이지 시작)
    ② 배너 셀 글자 HY헤드라인M 16pt (양식 실측: 참고1 배너 = HY헤드라인M 16Point)."""
    p_tag = qn("hp", "p")
    char_cache = {}
    pb_cache = {}
    banners = 0
    cell_runs = 0
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag:
                continue
            banner_tbls = [
                tbl for run in child.findall(qn("hp", "run"))
                for tbl in run.findall(qn("hp", "tbl"))
                if _is_banner_table(tbl)
            ]
            if not banner_tbls:
                continue
            banners += len(banner_tbls)
            base_pp = child.get("paraPrIDRef")
            if base_pp is not None:
                new_pp = ensure_pagebreak_parapr(header_root, base_pp, pb_cache)
                if new_pp != base_pp:
                    child.set("paraPrIDRef", new_pp)
            for tbl in banner_tbls:
                for cell_p in tbl.iter(p_tag):
                    for run in cell_p.findall(qn("hp", "run")):
                        base_id = run.get("charPrIDRef")
                        if base_id is None:
                            continue
                        new_id = ensure_charpr_font_size(
                            header_root, base_id, "HY헤드라인M", 1600, char_cache)
                        if new_id != base_id:
                            run.set("charPrIDRef", new_id)
                            cell_runs += 1
    return {"banners": banners, "cell_runs_changed": cell_runs}


def ensure_charpr_bold(header_root, base_id, cache):
    """base_id charPr에 볼드가 없으면 <hh:bold/>를 더한 복제본 id를 반환한다(있으면 그대로)."""
    if base_id in cache:
        return cache[base_id]
    charprops = header_root.find(f".//{qn('hh', 'charProperties')}")
    base = None
    for cp in charprops.findall(qn("hh", "charPr")):
        if cp.get("id") == base_id:
            base = cp
            break
    if base is None:
        cache[base_id] = base_id
        return base_id
    if base.find(qn("hh", "bold")) is not None:
        cache[base_id] = base_id
        return base_id
    new_cp = copy.deepcopy(base)
    max_id = max(int(cp.get("id")) for cp in charprops.findall(qn("hh", "charPr")))
    new_id = str(max_id + 1)
    new_cp.set("id", new_id)
    ET.SubElement(new_cp, qn("hh", "bold"))
    charprops.append(new_cp)
    charprops.set("itemCnt", str(int(charprops.get("itemCnt", "0")) + 1))
    cache[base_id] = new_id
    return new_id


def apply_dae_bold(header_root, section_roots):
    """□ 절 제목 문단 run의 charPr을 볼드 변형으로 치환한다(R024 — 사용자 확정 '26.7.24)."""
    p_tag = qn("hp", "p")
    cache = {}
    found = 0
    changed = 0
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag or classify(child) != "dae":
                continue
            found += 1
            for run in child.findall(qn("hp", "run")):
                base_id = run.get("charPrIDRef")
                if base_id is None:
                    continue
                new_id = ensure_charpr_bold(header_root, base_id, cache)
                if new_id != base_id:
                    run.set("charPrIDRef", new_id)
                    changed += 1
    return {"dae_found": found, "runs_changed": changed}


# KCA 양식 편집용지 여백 (HWPUNIT, 7200/inch): 좌우 20mm·위 10mm·아래 15mm·머리말 15mm·꼬리말 10mm
PAGE_MARGINS = {"left": "5669", "right": "5669", "top": "2835", "bottom": "4252",
                "header": "4252", "footer": "2835"}


def apply_page_margins(section_roots):
    """pagePr 여백을 KCA 양식 규격으로 강제한다 (kordoc preset은 위 15mm로 생성 —
    양식은 위 10mm라 제목표 위에 5mm 초과 여백이 생기는 결함의 후처리, R020)."""
    changed = 0
    for sec_root in section_roots:
        for pagepr in sec_root.iter(qn("hp", "pagePr")):
            margin = pagepr.find(qn("hp", "margin"))
            if margin is None:
                continue
            for k, v in PAGE_MARGINS.items():
                if margin.get(k) != v:
                    margin.set(k, v)
                    changed += 1
    return {"attrs_changed": changed}


HIERARCHY_SPACES = {"dae": 0, "yo": 1, "dash": 3, "star": 5, "cham": 5, "arrow": 5}
# 줄바꿈 시 둘째 줄 들여쓰기(=본문 시작 위치, HWPUNIT). 첫 줄은 intent=-left로 0에서 시작
# ※ 값은 폰트 크기가 아니라 "그 폰트 글자폭의 배수"(□1.5글자·ㅇ2글자·대시2.5글자·＊4글자) — 사용자 보고 시 글자 단위 병기
# (리터럴 공백이 마커 위치를 잡고, 랩된 줄은 left 위치에 정렬 — 사용자 확정 '26.7.22)
# 산출: 공백폭=글자크기/2 — dae 0+□15+공백7.5 / yo 공백7.5+ㅇ15+7.5 / dash 22.5+대시7.5+7.5
#       star·cham(13pt) 공백 5×6.5+기호13+6.5 / arrow(15pt 본문) 공백 5×7.5+기호15+7.5 (R025)
HIERARCHY_HANG = {"dae": 2250, "yo": 3000, "dash": 3750, "star": 5200, "cham": 5200,
                  "arrow": 6000}


def ensure_hang_parapr(header_root, base_id, hang, cache):
    """base paraPr 복제 — left=hang·intent=-hang(첫 줄 0에서 시작, 랩 줄은 hang 위치 정렬),
    prev·next=0. hang=0이면 전부 0(내어쓰기 불필요 계층)."""
    key = (base_id, hang)
    if key in cache:
        return cache[key]
    paraprops = header_root.find(f".//{qn('hh', 'paraProperties')}")
    base = None
    for pp in paraprops.findall(qn("hh", "paraPr")):
        if pp.get("id") == base_id:
            base = pp
            break
    if base is None:
        cache[key] = base_id
        return base_id
    # 한글 내어쓰기 의미론: 음수 intent = "첫 줄은 left 위치, 랩 줄은 left+|intent|"
    # → 첫 줄을 0(리터럴 띄어쓰기만)에 두려면 left=0·intent=-hang (원본 양식도 이 인코딩)
    want = {"left": "0", "intent": str(-hang), "prev": "0", "next": "0"}
    margin = base.find(qn("hh", "margin"))
    if margin is not None and all(
        (el := margin.find(qn("hc", t))) is not None and el.get("value") == v
        for t, v in want.items()
    ):
        cache[key] = base_id
        return base_id
    new_pp = copy.deepcopy(base)
    max_id = max(int(pp.get("id")) for pp in paraprops.findall(qn("hh", "paraPr")))
    new_id = str(max_id + 1)
    new_pp.set("id", new_id)
    nm = new_pp.find(qn("hh", "margin"))
    if nm is not None:
        for t, v in want.items():
            el = nm.find(qn("hc", t))
            if el is not None:
                el.set("value", v)
    paraprops.append(new_pp)
    paraprops.set("itemCnt", str(len(paraprops.findall(qn("hh", "paraPr")))))
    cache[key] = new_id
    return new_id


def apply_space_hierarchy(header_root, section_roots):
    """계층 표현을 paraPr 들여쓰기 대신 리터럴 띄어쓰기로 전환한다(사용자 확정 '26.7.22):
    □ 0칸 / ㅇ 1칸 / 대시 3칸 / ＊·※ 5칸. 해당 문단 paraPr의 left·intent는 0화(복제 배정)."""
    p_tag = qn("hp", "p")
    cache = {}
    changed = {"prefixed": 0, "flattened": 0}
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag:
                continue
            kind = classify(child)
            if kind not in HIERARCHY_SPACES:
                continue
            spaces = " " * HIERARCHY_SPACES[kind]
            for run in child.findall(qn("hp", "run")):
                t = run.find(qn("hp", "t"))
                if t is not None and t.text and t.text.strip():
                    canonical = spaces + t.text.lstrip(" ")
                    if t.text != canonical:
                        t.text = canonical
                        changed["prefixed"] += 1
                    break
            base_id = child.get("paraPrIDRef")
            if base_id is not None:
                hang = HIERARCHY_HANG.get(kind, 0)
                new_id = ensure_hang_parapr(header_root, base_id, hang, cache)
                if new_id != base_id:
                    child.set("paraPrIDRef", new_id)
                    changed["flattened"] += 1
    return changed


def ensure_charpr_sized(header_root, base_id, height, cache):
    """base_id charPr을 폰트는 유지한 채 height(HWPUNIT)만 바꾼 복제본 id를 반환한다."""
    key = (base_id, height)
    if key in cache:
        return cache[key]
    charprops = header_root.find(f".//{qn('hh', 'charProperties')}")
    base = None
    for cp in charprops.findall(qn("hh", "charPr")):
        if cp.get("id") == base_id:
            base = cp
            break
    if base is None:
        cache[key] = base_id
        return base_id
    if base.get("height") == str(height):
        cache[key] = base_id
        return base_id
    new_cp = copy.deepcopy(base)
    max_id = max(int(cp.get("id")) for cp in charprops.findall(qn("hh", "charPr")))
    new_id = str(max_id + 1)
    new_cp.set("id", new_id)
    new_cp.set("height", str(height))
    charprops.append(new_cp)
    charprops.set("itemCnt", str(int(charprops.get("itemCnt", "0")) + 1))
    cache[key] = new_id
    return new_id


def apply_sender_size(header_root, section_roots, pt):
    """발신 줄(classify=='sending') 문단 run의 charPr 크기를 pt로 치환한다."""
    height = int(round(pt * 100))
    p_tag = qn("hp", "p")
    cache = {}
    found = 0
    changed = 0
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag or classify(child) != "sending":
                continue
            found += 1
            for run in child.findall(qn("hp", "run")):
                base_id = run.get("charPrIDRef")
                if base_id is None:
                    continue
                new_id = ensure_charpr_sized(header_root, base_id, height, cache)
                if new_id != base_id:
                    run.set("charPrIDRef", new_id)
                    changed += 1
    return {"height": height, "sending_found": found, "runs_changed": changed}


def ensure_indent_parapr(header_root, base_id, left, intent, cache):
    """base_id paraPr을 margin.left=left·margin.intent=intent(HWPUNIT, 음수 허용)로
    바꾼 복제본 id를 반환한다. prev/next 여백은 base 값을 그대로 유지한다."""
    key = (base_id, left, intent)
    if key in cache:
        return cache[key]
    paraprops = header_root.find(f".//{qn('hh', 'paraProperties')}")
    base = None
    for pp in paraprops.findall(qn("hh", "paraPr")):
        if pp.get("id") == base_id:
            base = pp
            break
    if base is None:
        cache[key] = base_id
        return base_id
    margin = base.find(qn("hh", "margin"))
    if margin is not None:
        cur_left = margin.find(qn("hc", "left"))
        cur_intent = margin.find(qn("hc", "intent"))
        if (cur_left is not None and cur_left.get("value") == str(left)
                and cur_intent is not None and cur_intent.get("value") == str(intent)):
            cache[key] = base_id
            return base_id
    new_pp = copy.deepcopy(base)
    max_id = max(int(pp.get("id")) for pp in paraprops.findall(qn("hh", "paraPr")))
    new_id = str(max_id + 1)
    new_pp.set("id", new_id)
    nmargin = new_pp.find(qn("hh", "margin"))
    if nmargin is not None:
        nleft = nmargin.find(qn("hc", "left"))
        nintent = nmargin.find(qn("hc", "intent"))
        if nleft is not None:
            nleft.set("value", str(left))
        if nintent is not None:
            nintent.set("value", str(intent))
    paraprops.append(new_pp)
    paraprops.set("itemCnt", str(int(paraprops.get("itemCnt", "0")) + 1))
    cache[key] = new_id
    return new_id


def apply_star_indent(header_root, section_roots, left_pt, intent_pt):
    """＊·※ 문단의 paraPr을 left=left_pt(pt)·intent=intent_pt(pt, 음수 허용)로 치환한다."""
    left = int(round(left_pt * 100))
    intent = int(round(intent_pt * 100))
    p_tag = qn("hp", "p")
    cache = {}
    found = 0
    changed = 0
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag != p_tag or classify(child) not in ("star", "cham"):
                continue
            found += 1
            base_id = child.get("paraPrIDRef")
            if base_id is None:
                continue
            new_id = ensure_indent_parapr(header_root, base_id, left, intent, cache)
            if new_id != base_id:
                child.set("paraPrIDRef", new_id)
                changed += 1
    return {"left": left, "intent": intent, "found": found, "changed": changed}


CONTENT_KINDS = {"sending", "dae", "yo", "dash", "star", "cham", "arrow", "caption", "table",
                 "other"}


def apply_zero_margins(header_root, section_roots):
    """본문 최상위 콘텐츠 문단이 참조하는 paraPr의 위/아래 여백(prev/next)을 0으로.
    원본 양식 실측: 문단 여백 전부 0, 간격은 스페이서 문단만 담당 — kordoc preset이 넣는
    큰 위 여백(□ 30pt·ㅇ 20pt·대시 12pt)과 스페이서의 이중 간격을 제거한다."""
    p_tag = qn("hp", "p")
    used = set()
    for sec_root in section_roots:
        for child in sec_root:
            if child.tag == p_tag and classify(child) in CONTENT_KINDS:
                pid = child.get("paraPrIDRef")
                if pid is not None:
                    used.add(pid)
    zeroed = []
    for para_pr in header_root.iter(qn("hh", "paraPr")):
        if para_pr.get("id") not in used:
            continue
        margin = para_pr.find(qn("hh", "margin"))
        if margin is None:
            continue
        changed = {}
        for name in ("prev", "next"):
            el = margin.find(qn("hc", name))
            if el is not None and el.get("value") not in (None, "0"):
                changed[name] = el.get("value")
                el.set("value", "0")
        if changed:
            zeroed.append({"paraPr": para_pr.get("id"), "old": changed})
    return {"zeroed": zeroed, "count": len(zeroed)}


def effective_gaps(header_root, section_roots):
    """인접 콘텐츠 문단 쌍의 실효 간격(pt) = 사이 스페이서/빈 문단 charPr 높이 합
    + 다음 문단 paraPr.prev 여백. 검증 리포트용."""
    heights = {c.get("id"): int(c.get("height", "0")) for c in header_root.iter(qn("hh", "charPr"))}
    prevs = {}
    for para_pr in header_root.iter(qn("hh", "paraPr")):
        el = para_pr.find(qn("hh", "margin") + "/" + qn("hc", "prev")) if False else None
        margin = para_pr.find(qn("hh", "margin"))
        v = 0
        if margin is not None:
            pe = margin.find(qn("hc", "prev"))
            if pe is not None:
                v = int(pe.get("value", "0"))
        prevs[para_pr.get("id")] = v
    p_tag = qn("hp", "p")
    gaps = []
    for sec_root in section_roots:
        pending = 0
        prev_label = None
        for child in sec_root:
            if child.tag != p_tag:
                continue
            kind = classify(child)
            if kind == "empty":
                run = child.find(qn("hp", "run"))
                cid = run.get("charPrIDRef") if run is not None else None
                pending += heights.get(cid, 0)
                continue
            if kind in CONTENT_KINDS:
                if prev_label is not None:
                    total = pending + prevs.get(child.get("paraPrIDRef"), 0)
                    gaps.append({"between": f"{prev_label}→{kind}", "gap_pt": total / 100})
                prev_label = kind
                pending = 0
    return gaps


# ---------------------------------------------------------------------------
# zip 입출력
# ---------------------------------------------------------------------------

def serialize_xml(root):
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n' + body).encode("utf-8")


def process_file(path, star=False, spacing=False, sender_size=None, star_indent=None):
    if not (star or spacing or sender_size is not None or star_indent is not None):
        raise PostprocessError(
            "--star-footnote/--spacing/--sender-size/--star-indent/--all 중 최소 하나는 지정해야 합니다"
        )

    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        data = {info.filename: z.read(info.filename) for info in infos}

    header_root = ET.fromstring(data["Contents/header.xml"])
    section_names = sorted(n for n in data if SECTION_RE.match(n))
    section_roots = {n: ET.fromstring(data[n]) for n in section_names}

    summary = {"file": str(path), "sections": section_names}
    any_change = False
    any_target_found = False

    zero = spacing  # 스페이서 방식은 여백 0화와 한 몸 (원본 양식 정합)

    if star:
        r = apply_star_footnote(header_root, list(section_roots.values()))
        summary["star_footnote"] = r
        if r["stars_found"] > 0:
            any_target_found = True
        if r["runs_changed"] > 0:
            any_change = True

    if spacing:
        r = apply_spacing(header_root, list(section_roots.values()))
        summary["spacing"] = {"inserted": r["inserted"], "modified": r["modified"],
                               "events": r["events"]}
        if r["events"]:
            any_target_found = True
            any_change = True

    if zero:
        zr = apply_zero_margins(header_root, list(section_roots.values()))
        summary["zero_margins"] = zr
        if zr["count"] > 0:
            any_target_found = True
            any_change = True
        summary["effective_gaps"] = effective_gaps(header_root, list(section_roots.values()))
        cr = apply_center_tables(header_root, list(section_roots.values()))
        summary["center_tables"] = cr
        if cr["centered"]["caption"] or cr["centered"]["table"]:
            any_target_found = True
            any_change = True
        sh = apply_space_hierarchy(header_root, list(section_roots.values()))
        summary["space_hierarchy"] = sh
        if sh["prefixed"] or sh["flattened"]:
            any_target_found = True
            any_change = True
        pm = apply_page_margins(list(section_roots.values()))
        summary["page_margins"] = pm
        if pm["attrs_changed"]:
            any_target_found = True
            any_change = True

        ccr = apply_center_cell_text(header_root, list(section_roots.values()))
        summary["center_cells"] = ccr
        if ccr["tables"] > 0:
            any_target_found = True
        if ccr["paragraphs"] > 0:
            any_change = True

        tbr = apply_title_box_borderless(header_root, list(section_roots.values()))
        summary["title_box"] = tbr
        if tbr["found"]:
            any_target_found = True
        if tbr["fills_replaced"] > 0:
            any_change = True

        tgr = apply_title_box_topgap(header_root, list(section_roots.values()))
        summary["title_box_topgap"] = tgr
        if tgr["anchors_fixed"] or tgr["outmargins_fixed"]:
            any_target_found = True
            any_change = True

        cfr = apply_caption_table_font(header_root, list(section_roots.values()))
        summary["caption_table_font"] = cfr
        if cfr["caption_runs_changed"] or cfr["cell_runs_changed"]:
            any_target_found = True
            any_change = True

        dbr = apply_dae_bold(header_root, list(section_roots.values()))
        summary["dae_bold"] = dbr
        if dbr["dae_found"] > 0:
            any_target_found = True
        if dbr["runs_changed"] > 0:
            any_change = True

        abr = apply_annex_banner(header_root, list(section_roots.values()))
        summary["annex_banner"] = abr
        if abr["banners"] > 0:
            any_target_found = True
        if abr["cell_runs_changed"] > 0:
            any_change = True

    if sender_size is not None:
        ssr = apply_sender_size(header_root, list(section_roots.values()), sender_size)
        summary["sender_size"] = ssr
        if ssr["sending_found"] > 0:
            any_target_found = True
        if ssr["runs_changed"] > 0:
            any_change = True

    if star_indent is not None:
        left_pt, intent_pt = star_indent
        sir = apply_star_indent(header_root, list(section_roots.values()), left_pt, intent_pt)
        summary["star_indent"] = sir
        if sir["found"] > 0:
            any_target_found = True
        if sir["changed"] > 0:
            any_change = True

    data["Contents/header.xml"] = serialize_xml(header_root)
    for name, root in section_roots.items():
        data[name] = serialize_xml(root)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(pathlib.Path(path).resolve().parent), suffix=".hwpx.tmp")
    os.close(tmp_fd)
    try:
        with zipfile.ZipFile(tmp_path, "w") as zout:
            for info in infos:
                zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = info.compress_type
                zi.external_attr = info.external_attr
                zout.writestr(zi, data[info.filename])
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    summary["changed"] = any_change
    summary["target_found"] = any_target_found
    return summary


USAGE = ("usage: postprocess_hwpx.py <file.hwpx> [--star-footnote] [--spacing] [--all]\n"
         "                          [--sender-size PT] [--star-indent LEFT,INTENT]\n"
         "exit 0: 변경 적용 완료 | exit 1: 대상 없음(무변경) | exit 2: 인자/파일/구조 오류")


def main(argv):
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 2
    path, rest = argv[0], argv[1:]
    valid_bool = {"--star-footnote", "--spacing", "--all"}
    star = spacing = all_flag = False
    sender_size = None
    star_indent = None
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg in valid_bool:
            if arg == "--star-footnote":
                star = True
            elif arg == "--spacing":
                spacing = True
            else:
                all_flag = True
            i += 1
        elif arg == "--sender-size":
            if i + 1 >= len(rest):
                print(USAGE, file=sys.stderr)
                return 2
            try:
                sender_size = float(rest[i + 1])
            except ValueError:
                print(USAGE, file=sys.stderr)
                return 2
            i += 2
        elif arg == "--star-indent":
            if i + 1 >= len(rest):
                print(USAGE, file=sys.stderr)
                return 2
            parts = rest[i + 1].split(",")
            if len(parts) != 2:
                print(USAGE, file=sys.stderr)
                return 2
            try:
                star_indent = (float(parts[0]), float(parts[1]))
            except ValueError:
                print(USAGE, file=sys.stderr)
                return 2
            i += 2
        else:
            print(USAGE, file=sys.stderr)
            return 2

    star = star or all_flag
    spacing = spacing or all_flag
    if not (star or spacing or sender_size is not None or star_indent is not None):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        summary = process_file(path, star=star, spacing=spacing,
                                sender_size=sender_size, star_indent=star_indent)
    except PostprocessError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False))
    if not summary["target_found"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
