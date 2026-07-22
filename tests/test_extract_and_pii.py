import sys, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/report-pipeline/scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
from extract_format_profile import render_profile
from pii_scan import scan_dir

def test_render_profile_table():
    spec = {"elements": {"문서 제목": {"font": "HY헤드라인M", "pt": 20}},
            "page": {"여백": "좌20 우20 위10 아래15", "줄간격": "160%"}}
    md = render_profile(spec, source="test.hwp")
    assert "| 문서 제목 | HY헤드라인M | 20pt |" in md and "160%" in md

def test_pii_scan_detects(tmp_path):
    (tmp_path / "a.md").write_text("문의: 061-350-1565 mail@kca.kr")
    hits = scan_dir(tmp_path)
    assert len(hits) == 2

def test_pii_scan_clean(tmp_path):
    (tmp_path / "a.md").write_text("연락처는 마스킹됨 061-***-****")
    assert scan_dir(tmp_path) == []

def test_pii_scan_no_hyphen_phone(tmp_path):
    (tmp_path / "a.md").write_text("연락처 01012345678 / 010 1234 5678 / 010.1234.5678")
    kinds = [h["kind"] for h in scan_dir(tmp_path)]
    assert kinds.count("phone") >= 3

def test_pii_scan_extra_extensions(tmp_path):
    (tmp_path / "a.csv").write_text("name,phone\n김,061-350-1565")
    (tmp_path / "b.jsonl").write_text('{"mail":"x@kca.kr"}')
    (tmp_path / "c.yaml").write_text("tel: 010-1234-5678")
    kinds = {h["kind"] for h in scan_dir(tmp_path)}
    assert kinds == {"phone", "email"}

def test_pii_scan_no_false_positive_on_dates(tmp_path):
    (tmp_path / "a.md").write_text("사업기간 2026.01.13 ~ 2026.12.31, 예산 349,850,000원")
    assert scan_dir(tmp_path) == []
