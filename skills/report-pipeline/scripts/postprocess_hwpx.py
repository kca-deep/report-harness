#!/usr/bin/env python3
"""kordoc generate_document 산출 hwpx를 양식 정합으로 후처리한다 (stdlib-only).

기능 2종:
  --star-footnote  ＊ 시작 문단의 run charPrIDRef를 참고 스타일(header.xml에서
                    height=1300·fontRef=맑은고딕 계열)로 치환한다. kordoc은 ※만
                    참고 스타일로 인식하고 전각 ＊는 본문 스타일로 남는 결함의 후처리
                    (기존 수동 zip 패치의 스크립트화, R011).
  --spacing         계층 전환 지점(발신줄→□/□→ㅇ/ㅇ→-/-→＊/＊→표캡션/블록 구분)의
                    간격을 원본 KCA 양식 실측값(스페이서 문단 방식)으로 재현한다.
                    전환 지점에 이미 빈 문단이 있으면 그 charPr 높이를 치환하고,
                    없으면 새 스페이서 문단을 삽입한다.
  --all             위 두 기능을 모두 적용.

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
DAE, STAR, CHAM, DASH = "□", "＊", "※", "-"
YO_CHARS = ("ㅇ", "○")

# 전환 유형 → (이름, 스페이서 charPr 높이 HWPUNIT = pt*100)
TRANSITIONS = {
    ("sending", "dae"): ("sending_to_dae", 800),
    ("dae", "yo"): ("dae_to_yo", 600),
    ("yo", "dash"): ("yo_to_dash", 600),
    ("dash", "star"): ("dash_to_star", 300),
    ("star", "caption"): ("star_to_caption", 1000),
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


# ---------------------------------------------------------------------------
# zip 입출력
# ---------------------------------------------------------------------------

def serialize_xml(root):
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n' + body).encode("utf-8")


def process_file(path, star=False, spacing=False):
    if not (star or spacing):
        raise PostprocessError("--star-footnote/--spacing/--all 중 최소 하나는 지정해야 합니다")

    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        data = {info.filename: z.read(info.filename) for info in infos}

    header_root = ET.fromstring(data["Contents/header.xml"])
    section_names = sorted(n for n in data if SECTION_RE.match(n))
    section_roots = {n: ET.fromstring(data[n]) for n in section_names}

    summary = {"file": str(path), "sections": section_names}
    any_change = False
    any_target_found = False

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
         "exit 0: 변경 적용 완료 | exit 1: 대상 없음(무변경) | exit 2: 인자/파일/구조 오류")


def main(argv):
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 2
    path, flags = argv[0], set(argv[1:])
    valid = {"--star-footnote", "--spacing", "--all"}
    if not flags or not flags <= valid:
        print(USAGE, file=sys.stderr)
        return 2
    star = "--star-footnote" in flags or "--all" in flags
    spacing = "--spacing" in flags or "--all" in flags
    try:
        summary = process_file(path, star=star, spacing=spacing)
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
