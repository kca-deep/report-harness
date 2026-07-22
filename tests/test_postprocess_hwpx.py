import sys, pathlib, zipfile, io, re
import xml.etree.ElementTree as ET
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
import postprocess_hwpx as ph

NS = ph.NS

HEADER_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" version="1.4" secCnt="1">
  <hh:refList>
    <hh:fontfaces itemCnt="1">
      <hh:fontface lang="HANGUL" fontCnt="2">
        <hh:font id="0" face="휴먼명조" type="TTF" isEmbedded="0"/>
        <hh:font id="1" face="맑은고딕" type="TTF" isEmbedded="0"/>
      </hh:fontface>
    </hh:fontfaces>
    <hh:borderFills itemCnt="2">
      <hh:borderFill id="1" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">
        <hh:slash type="NONE" Crooked="0" isCounter="0"/>
        <hh:backSlash type="NONE" Crooked="0" isCounter="0"/>
        <hh:leftBorder type="SOLID" width="0.12 mm" color="#000000"/>
        <hh:rightBorder type="SOLID" width="0.12 mm" color="#000000"/>
        <hh:topBorder type="SOLID" width="0.12 mm" color="#000000"/>
        <hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000"/>
      </hh:borderFill>
      <hh:borderFill id="2" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">
        <hh:slash type="NONE" Crooked="0" isCounter="0"/>
        <hh:backSlash type="NONE" Crooked="0" isCounter="0"/>
        <hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>
        <hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>
        <hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>
        <hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>
      </hh:borderFill>
    </hh:borderFills>
    <hh:charProperties itemCnt="2">
      <hh:charPr id="0" height="1500" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="1">
        <hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
      </hh:charPr>
      <hh:charPr id="1" height="1300" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="1">
        <hh:fontRef hangul="1" latin="1" hanja="1" japanese="1" other="1" symbol="1" user="1"/>
        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
      </hh:charPr>
    </hh:charProperties>
    <hh:paraProperties itemCnt="1">
      <hh:paraPr id="0" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="0" suppressLineNumbers="0" checked="0" textDir="AUTO">
        <hh:align horizontal="JUSTIFY" vertical="BASELINE"/>
        <hh:heading type="NONE" idRef="0" level="0"/>
        <hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="BREAK_WORD" widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>
        <hh:autoSpacing eAsianEng="0" eAsianNum="0"/>
        <hh:margin>
          <hc:intent value="0" unit="HWPUNIT"/>
          <hc:left value="0" unit="HWPUNIT"/>
          <hc:right value="0" unit="HWPUNIT"/>
          <hc:prev value="0" unit="HWPUNIT"/>
          <hc:next value="0" unit="HWPUNIT"/>
        </hh:margin>
        <hh:lineSpacing type="PERCENT" value="160"/>
        <hh:border borderFillIDRef="1" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0"/>
      </hh:paraPr>
    </hh:paraProperties>
  </hh:refList>
</hh:head>
"""

# 시나리오: 발신줄 → □1 → ㅇ1 → -1 → ＊1(본문 charPr, 치환 대상) → 캡션 → 표(＊→캡션 간
# 스페이서 삽입 검증) → (기존 빈 문단, 표→□ 전환 modify 검증) → □2 → ㅇ2 → □3(ㅇ→□ 블록
# 구분 insert 검증)
SECTION_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>&lt; '26. 1. 1.(목), 테스트팀 &gt;</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>□ 제목1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>- 상세1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>＊ 각주1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>[ 표 제목 ]</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:tbl id="1" rowCnt="1" colCnt="1"><hp:tr><hp:tc><hp:subList><hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>셀</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t/></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>□ 제목2</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지2</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>□ 제목3</hp:t></hp:run></hp:p>
</hs:sec>
"""

MIMETYPE = b"application/hwp+zip"


def build_hwpx(path, header_xml=HEADER_XML, section_xml=SECTION_XML):
    with zipfile.ZipFile(path, "w") as z:
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, MIMETYPE)
        z.writestr("META-INF/container.xml", "<container/>")
        z.writestr("Contents/content.hpf", "<opf:package xmlns:opf='x'/>")
        z.writestr("Contents/header.xml", header_xml)
        z.writestr("Contents/section0.xml", section_xml)
    return path


def all_text_and_ids(section_xml_bytes):
    """비파괴 검증용: 텍스트가 있는 문단의 (텍스트, charPrIDRef) 목록만 추린다(스페이서 제외)."""
    root = ET.fromstring(section_xml_bytes)
    out = []
    for p in root.iter(ph.qn("hp", "p")):
        for run in p.findall(ph.qn("hp", "run")):
            t = run.find(ph.qn("hp", "t"))
            if t is not None and t.text:
                out.append((t.text, run.get("charPrIDRef")))
    return out


@pytest.fixture
def hwpx_file(tmp_path):
    p = tmp_path / "sample.hwpx"
    build_hwpx(str(p))
    return p


def test_classify_symbols():
    mkp = lambda text: ET.fromstring(
        f'<hp:p xmlns:hp="{NS["hp"]}" paraPrIDRef="0"><hp:run charPrIDRef="0"><hp:t>{text}</hp:t></hp:run></hp:p>'
    )
    assert ph.classify(mkp("□ 제목")) == "dae"
    assert ph.classify(mkp("ㅇ 요지")) == "yo"
    assert ph.classify(mkp("- 상세")) == "dash"
    assert ph.classify(mkp("＊ 각주")) == "star"
    assert ph.classify(mkp("※ 참조")) == "cham"
    assert ph.classify(mkp("&lt; '26. 1. 1.(목), 팀 &gt;")) == "sending"
    assert ph.classify(mkp("[ 표 제목 ]")) == "caption"


def test_transition_lookup_values():
    assert ph.transition_for("sending", "dae") == ("sending_to_dae", 800)
    assert ph.transition_for("dae", "yo") == ("dae_to_yo", 600)
    assert ph.transition_for("yo", "dash") == ("yo_to_dash", 600)
    assert ph.transition_for("dash", "star") == ("dash_to_star", 300)
    assert ph.transition_for("star", "caption") == ("star_to_caption", 1000)
    assert ph.transition_for("yo", "dae") == ("block_boundary", 1500)
    assert ph.transition_for("table", "dae") == ("block_boundary", 1500)
    assert ph.transition_for("yo", "yo") == ("yo_to_yo", 600)  # 사용자 확정('26.7.22): 연속 ㅇ 6pt
    assert ph.transition_for("dash", "dash") is None


# --- ①＊ 치환 -----------------------------------------------------------

def test_star_footnote_replaces_charpr(hwpx_file):
    summary = ph.process_file(str(hwpx_file), star=True, spacing=False)
    assert summary["star_footnote"]["ref_charpr_id"] == "1"
    assert summary["star_footnote"]["stars_found"] == 1
    assert summary["star_footnote"]["runs_changed"] == 1
    with zipfile.ZipFile(hwpx_file) as z:
        sec = z.read("Contents/section0.xml")
    pairs = dict(all_text_and_ids(sec))
    assert pairs["＊ 각주1"] == "1"


def test_star_footnote_idempotent(hwpx_file):
    ph.process_file(str(hwpx_file), star=True, spacing=False)
    summary2 = ph.process_file(str(hwpx_file), star=True, spacing=False)
    assert summary2["star_footnote"]["stars_found"] == 1
    assert summary2["star_footnote"]["runs_changed"] == 0  # 이미 치환됨 — 재실행 안전


def test_star_footnote_missing_ref_raises(tmp_path):
    header_no_ref = HEADER_XML.replace(
        '<hh:font id="1" face="맑은고딕" type="TTF" isEmbedded="0"/>',
        '<hh:font id="1" face="휴먼명조" type="TTF" isEmbedded="0"/>',
    )
    p = tmp_path / "noref.hwpx"
    build_hwpx(str(p), header_xml=header_no_ref)
    with pytest.raises(ph.PostprocessError):
        ph.process_file(str(p), star=True, spacing=False)


# --- ②전환 유형별 스페이서 높이 판정 ---------------------------------------

def test_spacing_inserts_and_modifies(hwpx_file):
    summary = ph.process_file(str(hwpx_file), star=False, spacing=True)
    events = summary["spacing"]["events"]
    names = [e["transition"] for e in events]
    # insert 경로: 발신줄→□, □→ㅇ(x2), ㅇ→-, -→＊, ＊→캡션, ㅇ→□(블록구분)
    assert names.count("sending_to_dae") == 1
    assert names.count("dae_to_yo") == 2
    assert names.count("yo_to_dash") == 1
    assert names.count("dash_to_star") == 1
    assert names.count("star_to_caption") == 1
    assert names.count("block_boundary") == 2  # 표→□2(기존 빈 문단 modify) + ㅇ2→□3(insert)
    assert summary["spacing"]["modified"] == 1  # 표→□2 구간의 기존 빈 문단
    assert summary["spacing"]["inserted"] == len(events) - 1

    with zipfile.ZipFile(hwpx_file) as z:
        sec = ET.fromstring(z.read("Contents/section0.xml"))
        header = ET.fromstring(z.read("Contents/header.xml"))

    heights = {cp.get("id"): cp.get("height") for cp in header.iter(ph.qn("hh", "charPr"))}
    tops = list(sec)
    texts = [ph.para_text(p).strip() for p in tops]

    def height_of(p):
        run = p.find(ph.qn("hp", "run"))
        return heights[run.get("charPrIDRef")]

    idx_sending = texts.index("< '26. 1. 1.(목), 테스트팀 >")
    idx_dae1 = next(i for i, t in enumerate(texts) if t == "□ 제목1")
    assert idx_dae1 == idx_sending + 2  # 스페이서 한 칸 삽입됨
    assert height_of(tops[idx_dae1 - 1]) == "800"

    idx_yo1 = texts.index("ㅇ 요지1")
    assert height_of(tops[idx_yo1 - 1]) == "600"

    idx_dash1 = texts.index("- 상세1")
    assert height_of(tops[idx_dash1 - 1]) == "600"

    idx_star1 = texts.index("＊ 각주1")
    assert height_of(tops[idx_star1 - 1]) == "300"

    idx_caption = texts.index("[ 표 제목 ]")
    assert height_of(tops[idx_caption - 1]) == "1000"

    idx_dae2 = texts.index("□ 제목2")
    assert height_of(tops[idx_dae2 - 1]) == "1500"  # 표→□2, 기존 빈 문단 재활용(modify)

    idx_dae3 = texts.index("□ 제목3")
    assert height_of(tops[idx_dae3 - 1]) == "1500"  # ㅇ2→□3, 신규 삽입(insert)

    # 600 높이 charPr은 dae_to_yo가 두 번 나와도 재사용되어 신규 등록이 1개만 추가돼야 한다.
    height_values = [cp.get("height") for cp in header.iter(ph.qn("hh", "charPr"))]
    assert height_values.count("600") == 1


def test_spacing_yo_to_yo_inserts_6pt(tmp_path):
    section = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지2</hp:t></hp:run></hp:p>
</hs:sec>
"""
    p = tmp_path / "same_level.hwpx"
    build_hwpx(str(p), section_xml=section)
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert [e["transition"] for e in summary["spacing"]["events"]] == ["yo_to_yo"]
    assert summary["spacing"]["events"][0]["height"] == 600
    assert summary["target_found"] is True


# --- ③비파괴(텍스트 콘텐츠 불변) ------------------------------------------

def test_all_preserves_text_content(hwpx_file):
    with zipfile.ZipFile(hwpx_file) as z:
        before = [t for t, _ in all_text_and_ids(z.read("Contents/section0.xml"))]

    ph.process_file(str(hwpx_file), star=True, spacing=True)

    with zipfile.ZipFile(hwpx_file) as z:
        after = [t for t, _ in all_text_and_ids(z.read("Contents/section0.xml"))]

    assert before == after  # 삽입된 스페이서는 t 텍스트가 없어 비교 대상에서 제외됨(비파괴 확인)


def test_zip_structure_preserved(hwpx_file):
    with zipfile.ZipFile(hwpx_file) as z:
        names_before = z.namelist()
        mimetype_before = z.read("mimetype")

    ph.process_file(str(hwpx_file), star=True, spacing=True)

    with zipfile.ZipFile(hwpx_file) as z:
        assert z.namelist() == names_before
        assert z.namelist()[0] == "mimetype"
        assert z.read("mimetype") == mimetype_before
        bad = z.testzip()
        assert bad is None
        for n in z.namelist():
            if n.endswith(".xml"):
                ET.fromstring(z.read(n))  # 전체 xml 파싱 가능(구조 정상)


# --- CLI / exit code ------------------------------------------------------

def test_main_no_args_exit2(capsys):
    rc = ph.main([])
    assert rc == 2


def test_main_invalid_flag_exit2(hwpx_file, capsys):
    rc = ph.main([str(hwpx_file), "--bogus"])
    assert rc == 2


def test_main_all_success_exit0(hwpx_file, capsys):
    rc = ph.main([str(hwpx_file), "--all"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = __import__("json").loads(out)
    assert payload["changed"] is True


def test_main_nothing_to_do_exit1(tmp_path, capsys):
    section = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지1</hp:t></hp:run></hp:p>
</hs:sec>
"""
    p = tmp_path / "nothing.hwpx"
    build_hwpx(str(p), section_xml=section)
    rc = ph.main([str(p), "--spacing"])
    assert rc == 1


def test_main_missing_file_exit2(capsys):
    rc = ph.main(["/nonexistent/path/x.hwpx", "--all"])
    assert rc == 2


def test_yo_to_star_transition_inferred():
    from postprocess_hwpx import transition_for
    assert transition_for("yo", "star") == ("yo_to_star", 300)


def test_yo_to_yo_and_dash_to_yo_transitions():
    from postprocess_hwpx import transition_for
    assert transition_for("yo", "yo") == ("yo_to_yo", 600)
    assert transition_for("dash", "yo") == ("dash_to_yo", 600)


def test_zero_margins_removes_parapr_prev(tmp_path):
    # 콘텐츠 문단이 참조하는 paraPr의 prev/next 여백이 spacing 처리 시 0으로
    header = HEADER_XML.replace(
        '<hc:prev value="0" unit="HWPUNIT"/>',
        '<hc:prev value="3000" unit="HWPUNIT"/>')
    p = tmp_path / "zm.hwpx"
    build_hwpx(str(p), header_xml=header)
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert summary["zero_margins"]["count"] == 1
    assert summary["zero_margins"]["zeroed"][0]["old"]["prev"] == "3000"
    with zipfile.ZipFile(str(p)) as z:
        hdr = z.read("Contents/header.xml").decode()
    assert 'value="3000"' not in hdr
    # 실효 간격 리포트: □→ㅇ = 스페이서 6pt + prev 0
    gaps = {g["between"]: g["gap_pt"] for g in summary["effective_gaps"]}
    assert gaps.get("dae→yo") == 6.0


def test_center_tables_and_captions(tmp_path):
    p = tmp_path / "ct.hwpx"
    build_hwpx(str(p))
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert summary["center_tables"]["centered"]["caption"] >= 1
    assert summary["center_tables"]["centered"]["table"] >= 1
    with zipfile.ZipFile(str(p)) as z:
        hdr = z.read("Contents/header.xml").decode()
        sec = z.read("Contents/section0.xml").decode()
    assert 'horizontal="CENTER"' in hdr
    import re as _re
    i = sec.find("[ 표 제목 ]")
    seg = sec[max(0, i - 400):i]
    pid = _re.findall(r'paraPrIDRef="(\d+)"', seg)[-1]
    assert pid != "0"
    j = sec.find("ㅇ 요지1")
    seg2 = sec[max(0, j - 400):j]
    pid2 = _re.findall(r'paraPrIDRef="(\d+)"', seg2)[-1]
    assert pid2 == "0"


# --- ④표-문단 간격 보정 전환 값 -------------------------------------------

def test_new_table_spacing_transitions():
    assert ph.transition_for("caption", "table") == ("caption_to_table", 300)
    assert ph.transition_for("table", "cham") == ("table_to_cham", 300)
    assert ph.transition_for("yo", "caption") == ("yo_to_caption", 600)
    assert ph.transition_for("dash", "caption") == ("dash_to_caption", 600)
    assert ph.transition_for("cham", "caption") == ("cham_to_caption", 600)
    # table→dae 블록 경계 15pt는 유지(일반 block_boundary 규칙)
    assert ph.transition_for("table", "dae") == ("block_boundary", 1500)


# --- ⑤표 셀 텍스트 가운데 정렬(제목 박스 제외) -----------------------------

# 시나리오: 제목 박스 표(첫 □ 이전) → 발신줄 → □1 → 캡션 → 콘텐츠 표
TITLE_BOX_SECTION_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:tbl id="1" rowCnt="1" colCnt="1" borderFillIDRef="1"><hp:tr><hp:tc borderFillIDRef="1"><hp:subList><hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>제목텍스트</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>&lt; '26. 1. 1.(목), 테스트팀 &gt;</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>□ 제목1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>[ 표 제목 ]</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:tbl id="2" rowCnt="1" colCnt="1"><hp:tr><hp:tc><hp:subList><hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>셀값</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>
</hs:sec>
"""


def test_center_cell_text_excludes_title_box(tmp_path):
    p = tmp_path / "title_box.hwpx"
    build_hwpx(str(p), section_xml=TITLE_BOX_SECTION_XML)
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert summary["center_cells"]["tables"] == 1       # 제목 박스 표는 제외, 콘텐츠 표만 카운트
    assert summary["center_cells"]["paragraphs"] == 1

    with zipfile.ZipFile(p) as z:
        sec = z.read("Contents/section0.xml").decode()

    i_title_cell = sec.find("제목텍스트")
    seg_title = sec[max(0, i_title_cell - 200):i_title_cell]
    pid_title = re.findall(r'paraPrIDRef="(\d+)"', seg_title)[-1]
    assert pid_title == "0"  # 제목 박스 셀은 가운데 정렬 대상에서 제외되어 원래 paraPr 유지

    i_cell = sec.find("셀값")
    seg_cell = sec[max(0, i_cell - 200):i_cell]
    pid_cell = re.findall(r'paraPrIDRef="(\d+)"', seg_cell)[-1]
    assert pid_cell != "0"  # 콘텐츠 표 셀은 새 CENTER paraPr로 치환됨

    with zipfile.ZipFile(p) as z:
        hdr = z.read("Contents/header.xml").decode()
    m = re.search(rf'<hh:paraPr id="{pid_cell}"[^>]*>.*?</hh:paraPr>', hdr, re.S)
    assert 'horizontal="CENTER"' in m.group()


def test_center_cell_text_on_content_table(hwpx_file):
    summary = ph.process_file(str(hwpx_file), star=False, spacing=True)
    assert summary["center_cells"]["tables"] == 1
    assert summary["center_cells"]["paragraphs"] == 1
    with zipfile.ZipFile(hwpx_file) as z:
        hdr = z.read("Contents/header.xml").decode()
        sec = z.read("Contents/section0.xml").decode()
    i = sec.find("셀")
    seg = sec[max(0, i - 200):i]
    pid = re.findall(r'paraPrIDRef="(\d+)"', seg)[-1]
    assert pid != "0"
    m = re.search(rf'<hh:paraPr id="{pid}"[^>]*>.*?</hh:paraPr>', hdr, re.S)
    assert 'horizontal="CENTER"' in m.group()


# --- ⑥제목 박스 테두리 제거 -------------------------------------------------

def test_title_box_borderless_replaces_refs(tmp_path):
    p = tmp_path / "title_borderless2.hwpx"
    build_hwpx(str(p), section_xml=TITLE_BOX_SECTION_XML)
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert summary["title_box"]["found"] is True
    assert summary["title_box"]["fills_replaced"] >= 2  # hp:tbl + hp:tc 각각 치환
    with zipfile.ZipFile(p) as z:
        sec = z.read("Contents/section0.xml").decode()
    i = sec.find("제목텍스트")
    seg = sec[max(0, i - 400):i]
    # 원본(id=1, SOLID) 참조가 배경 보존 무테두리 변형으로 교체됨 ('26.7.22 개정)
    assert 'borderFillIDRef="1"' not in seg
    new_id = summary["title_box"]["variants"]["1"]
    assert f'borderFillIDRef="{new_id}"' in seg


def test_title_box_borderless_creates_fill_when_missing(tmp_path):
    header_no_borderless = HEADER_XML.replace(
        '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>\n'
        '        <hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>\n'
        '        <hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>\n'
        '        <hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>',
        '<hh:leftBorder type="SOLID" width="0.1 mm" color="#000000"/>\n'
        '        <hh:rightBorder type="SOLID" width="0.1 mm" color="#000000"/>\n'
        '        <hh:topBorder type="SOLID" width="0.1 mm" color="#000000"/>\n'
        '        <hh:bottomBorder type="SOLID" width="0.1 mm" color="#000000"/>',
    )
    bf_block = re.search(
        r'<hh:borderFills.*?</hh:borderFills>', header_no_borderless, re.S).group()
    assert 'Border type="NONE"' not in bf_block  # left/right/top/bottomBorder 전부 SOLID(대각선 slash/backSlash는 NONE 그대로)
    p = tmp_path / "title_borderless_new.hwpx"
    build_hwpx(str(p), header_xml=header_no_borderless, section_xml=TITLE_BOX_SECTION_XML)
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert summary["title_box"]["found"] is True
    assert summary["title_box"]["fills_replaced"] >= 2
    with zipfile.ZipFile(p) as z:
        hdr = z.read("Contents/header.xml").decode()
    assert 'itemCnt="3"' in re.search(r'<hh:borderFills itemCnt="(\d+)"', hdr).group()
    new_fill = re.search(r'<hh:borderFill id="3"[^>]*>.*?</hh:borderFill>', hdr, re.S).group()
    assert len(re.findall(r'Border type="NONE"', new_fill)) == 4  # left/right/top/bottom 전부 NONE
    assert 'slash type="NONE"' in new_fill  # 대각선(slash/backSlash)은 원본 그대로 보존(원래도 NONE)


def test_title_box_not_found_when_no_table_before_dae(hwpx_file):
    # hwpx_file(기존 SECTION_XML)은 첫 □ 이전에 표가 없다(첫 표는 □1 이후) → 제목 박스 없음
    summary = ph.process_file(str(hwpx_file), star=False, spacing=True)
    assert summary["title_box"]["found"] is False
    assert summary["title_box"]["fills_replaced"] == 0


def test_ensure_borderless_fill_idempotent(tmp_path):
    p = tmp_path / "idem.hwpx"
    build_hwpx(str(p), section_xml=TITLE_BOX_SECTION_XML)
    ph.process_file(str(p), star=False, spacing=True)
    summary2 = ph.process_file(str(p), star=False, spacing=True)
    assert summary2["title_box"]["found"] is True
    assert summary2["title_box"]["fills_replaced"] == 0  # 이미 치환됨 — 재실행 안전


# --- ⑦발신 크기 훅 ----------------------------------------------------------

def test_apply_sender_size_preserves_font(hwpx_file):
    summary = ph.process_file(str(hwpx_file), star=False, spacing=False, sender_size=13)
    r = summary["sender_size"]
    assert r["height"] == 1300
    assert r["sending_found"] == 1
    assert r["runs_changed"] == 1
    with zipfile.ZipFile(hwpx_file) as z:
        hdr = z.read("Contents/header.xml").decode()
        sec = z.read("Contents/section0.xml").decode()
    i = sec.find("테스트팀")
    seg = sec[max(0, i - 200):i]
    new_id = re.findall(r'charPrIDRef="(\d+)"', seg)[-1]
    assert new_id != "0"
    cp = re.search(rf'<hh:charPr id="{new_id}"[^>]*>.*?</hh:charPr>', hdr, re.S).group()
    assert 'height="1300"' in cp
    assert 'hangul="0"' in cp  # 발신 줄 원 charPr(id=0, 휴먼명조) 기반 복제 — 기존 height=1300(id=1, 맑은고딕)과 다른 폰트 유지


def test_apply_sender_size_idempotent(hwpx_file):
    ph.process_file(str(hwpx_file), star=False, spacing=False, sender_size=13)
    summary2 = ph.process_file(str(hwpx_file), star=False, spacing=False, sender_size=13)
    assert summary2["sender_size"]["runs_changed"] == 0


def test_apply_sender_size_no_sending_line(tmp_path):
    section = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지1</hp:t></hp:run></hp:p>
</hs:sec>
"""
    p = tmp_path / "nosend.hwpx"
    build_hwpx(str(p), section_xml=section)
    summary = ph.process_file(str(p), star=False, spacing=False, sender_size=13)
    assert summary["sender_size"]["sending_found"] == 0
    assert summary["target_found"] is False


# --- ⑧＊/※ 들여쓰기 훅 -------------------------------------------------------

def test_apply_star_indent_applies_to_star_and_cham(tmp_path):
    section = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>＊ 각주1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>※ 참조1</hp:t></hp:run></hp:p>
</hs:sec>
"""
    p = tmp_path / "indent.hwpx"
    build_hwpx(str(p), section_xml=section)
    summary = ph.process_file(str(p), star=False, spacing=False, star_indent=(15, -7.5))
    r = summary["star_indent"]
    assert r["left"] == 1500
    assert r["intent"] == -750
    assert r["found"] == 2
    assert r["changed"] == 2

    with zipfile.ZipFile(p) as z:
        hdr = z.read("Contents/header.xml").decode()
        sec = z.read("Contents/section0.xml").decode()

    i_star = sec.find("＊ 각주1")
    seg_star = sec[max(0, i_star - 200):i_star]
    pid_star = re.findall(r'paraPrIDRef="(\d+)"', seg_star)[-1]
    i_cham = sec.find("※ 참조1")
    seg_cham = sec[max(0, i_cham - 200):i_cham]
    pid_cham = re.findall(r'paraPrIDRef="(\d+)"', seg_cham)[-1]
    assert pid_star != "0" and pid_cham != "0"
    assert pid_star == pid_cham  # 동일 base(paraPrIDRef=0)·동일 값 → 같은 복제본 재사용

    pp = re.search(rf'<hh:paraPr id="{pid_star}"[^>]*>.*?</hh:paraPr>', hdr, re.S).group()
    assert '<hc:left value="1500"' in pp
    assert '<hc:intent value="-750"' in pp
    assert '<hc:prev value="0"' in pp  # prev/next 여백은 유지(변경 없음)
    assert '<hc:next value="0"' in pp


def test_apply_star_indent_idempotent(tmp_path):
    section = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>＊ 각주1</hp:t></hp:run></hp:p>
</hs:sec>
"""
    p = tmp_path / "indent2.hwpx"
    build_hwpx(str(p), section_xml=section)
    ph.process_file(str(p), star=False, spacing=False, star_indent=(15, -7.5))
    summary2 = ph.process_file(str(p), star=False, spacing=False, star_indent=(15, -7.5))
    assert summary2["star_indent"]["changed"] == 0


# --- CLI: --sender-size / --star-indent 파싱 -------------------------------

def test_main_sender_size_cli(hwpx_file, capsys):
    rc = ph.main([str(hwpx_file), "--sender-size", "13"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = __import__("json").loads(out)
    assert payload["sender_size"]["height"] == 1300
    assert "spacing" not in payload  # --spacing 미지정 시 다른 기능은 실행 안 됨


def test_main_star_indent_cli(hwpx_file, capsys):
    rc = ph.main([str(hwpx_file), "--star-indent", "15,-7.5"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = __import__("json").loads(out)
    assert payload["star_indent"]["left"] == 1500
    assert payload["star_indent"]["intent"] == -750


def test_main_sender_size_missing_value_exit2(hwpx_file):
    rc = ph.main([str(hwpx_file), "--sender-size"])
    assert rc == 2


def test_main_sender_size_non_numeric_exit2(hwpx_file):
    rc = ph.main([str(hwpx_file), "--sender-size", "abc"])
    assert rc == 2


def test_main_star_indent_bad_format_exit2(hwpx_file):
    rc = ph.main([str(hwpx_file), "--star-indent", "15"])
    assert rc == 2


def test_main_star_indent_non_numeric_exit2(hwpx_file):
    rc = ph.main([str(hwpx_file), "--star-indent", "a,b"])
    assert rc == 2


def test_main_all_does_not_include_sender_size_or_star_indent(hwpx_file, capsys):
    rc = ph.main([str(hwpx_file), "--all"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = __import__("json").loads(out)
    assert "sender_size" not in payload
    assert "star_indent" not in payload
    assert "center_cells" in payload   # 기능 1은 spacing 묶음으로 --all에 포함됨
    assert "title_box" in payload      # 기능 3도 spacing 묶음으로 --all에 포함됨


def test_main_all_plus_sender_size_combined(hwpx_file, capsys):
    rc = ph.main([str(hwpx_file), "--all", "--sender-size", "13"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = __import__("json").loads(out)
    assert payload["sender_size"]["height"] == 1300
    assert "center_cells" in payload


def test_title_box_keeps_gradient_fill(tmp_path):
    # 그라데이션 배경 + SOLID 테두리 borderFill을 참조하는 제목 박스 →
    # 테두리만 NONE, fillBrush(gradation) 보존된 변형으로 교체돼야 한다
    header = HEADER_XML.replace(
        "</hh:borderFills>",
        '''<hh:borderFill id="7" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">
      <hh:slash type="NONE" Crooked="0" isCounter="0"/>
      <hh:backSlash type="NONE" Crooked="0" isCounter="0"/>
      <hh:leftBorder type="SOLID" width="0.12 mm" color="#000000"/>
      <hh:rightBorder type="SOLID" width="0.12 mm" color="#000000"/>
      <hh:topBorder type="SOLID" width="0.12 mm" color="#000000"/>
      <hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000"/>
      <hc:fillBrush><hc:gradation type="LINEAR" angle="90"><hc:color value="#FFFFFF"/><hc:color value="#0066CC"/></hc:gradation></hc:fillBrush>
    </hh:borderFill></hh:borderFills>''')
    section = '''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:tbl id="1" rowCnt="1" colCnt="1" borderFillIDRef="7"><hp:tr><hp:tc borderFillIDRef="7"><hp:subList><hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>제목</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>□ 절</hp:t></hp:run></hp:p>
</hs:sec>
'''
    p = tmp_path / "grad.hwpx"
    build_hwpx(str(p), header_xml=header, section_xml=section)
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert summary["title_box"]["found"] is True
    assert summary["title_box"]["fills_replaced"] == 2
    import xml.etree.ElementTree as _ET
    with zipfile.ZipFile(str(p)) as z:
        hdr_root = _ET.fromstring(z.read("Contents/header.xml"))
        sec_txt = z.read("Contents/section0.xml").decode()
    new_id = summary["title_box"]["variants"]["7"]
    target = None
    for bf in hdr_root.iter(ph.qn("hh", "borderFill")):
        if bf.get("id") == new_id:
            target = bf
    assert target is not None
    for tname in ("leftBorder", "rightBorder", "topBorder", "bottomBorder"):
        assert target.find(ph.qn("hh", tname)).get("type") == "NONE"
    assert target.find(ph.qn("hc", "fillBrush")) is not None  # 그라데이션 보존
    assert f'borderFillIDRef="{new_id}"' in sec_txt
