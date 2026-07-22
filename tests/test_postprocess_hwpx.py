import sys, pathlib, zipfile, io
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
    assert ph.transition_for("yo", "yo") is None
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


def test_spacing_no_transition_between_same_level_items(tmp_path):
    section = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지1</hp:t></hp:run></hp:p>
  <hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>ㅇ 요지2</hp:t></hp:run></hp:p>
</hs:sec>
"""
    p = tmp_path / "same_level.hwpx"
    build_hwpx(str(p), section_xml=section)
    summary = ph.process_file(str(p), star=False, spacing=True)
    assert summary["spacing"]["events"] == []
    assert summary["target_found"] is False


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
