import sys, pathlib, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
from validate_hwpx import structural_check, profile_counts, compare_texts

def make_zip(tmp_path, xml=b"<?xml version='1.0'?><root/>"):
    p = tmp_path / "t.hwpx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("Contents/section0.xml", xml)
    return p

def test_structural_ok(tmp_path):
    assert structural_check(make_zip(tmp_path)) == []

def test_structural_broken_xml(tmp_path):
    errs = structural_check(make_zip(tmp_path, b"<root><unclosed>"))
    assert errs and "section0.xml" in errs[0]

def test_profile_counts():
    c = profile_counts("□ A\n ㅇ b 137명(23.7%)\n   - c\n＊ 각주\n| a | b |\n|---|---|\n")
    assert c["sections"] == 1 and c["points"] == 1 and c["subs"] == 1
    assert c["footnotes"] == 1 and c["tables"] == 1
    assert "137" in c["numbers"] and "23.7" in c["numbers"]

def test_compare_detects_lost_number_and_leftover():
    src = "□ A\n ㅇ 총 502건 정비\n"
    rt = "□ A\n ㅇ 총 **502**건 정비 - 그대로 노출\n"   # 볼드 기호·인라인 대시 잔재
    issues = {i["rule"] for i in compare_texts(src, rt)}
    assert "markdown-leftover" in issues

def test_compare_ok_when_identical():
    src = "□ A\n ㅇ 총 502건 정비\n"
    assert compare_texts(src, src) == []

def test_max_cols_loss_detected():         # 표 컬럼 유실 검출 (스펙 누락 보완)
    src = "| 구분 | 사업명 | 담당부서 |\n|---|---|---|\n| 1 | AI플랫폼 | 정보화기획팀 |\n"
    rt  = "| 구분 | 사업명 |\n|---|---|\n| 1 | AI플랫폼 |\n"
    assert any(i["rule"] == "count-mismatch:max_cols" for i in compare_texts(src, rt))

def test_backtick_leftover_detected():
    issues = compare_texts("ㅇ 코드 사용법\n", "ㅇ `코드` 사용법\n")
    assert any(i["rule"] == "markdown-leftover" for i in issues)

def test_double_hash_leftover_detected():
    issues = compare_texts("소제목\n", "## 소제목\n")
    assert any(i["rule"] == "markdown-leftover" for i in issues)

def test_hr_leftover_detected():
    issues = compare_texts("□ 제목\nㅇ 내용\n", "□ 제목\nㅇ 내용\n---\n")
    assert any(i["rule"] == "markdown-leftover" for i in issues)

def test_italic_strike_leftover_detected():
    assert any(i["rule"] == "markdown-leftover" for i in compare_texts("ㅇ 강조 문구\n", "ㅇ *강조* 문구\n"))
    assert any(i["rule"] == "markdown-leftover" for i in compare_texts("ㅇ 삭제 문구\n", "ㅇ ~~삭제~~ 문구\n"))

def test_number_reformat_not_lost():       # 표기 정규화는 손실 아님 (오탐 제거)
    assert compare_texts("ㅇ 예산 1,234백만원 편성\n", "ㅇ 예산 1234백만원 편성\n") == []
    assert compare_texts("ㅇ 비율 23.70%\n", "ㅇ 비율 23.7%\n") == []

def test_real_number_loss_still_detected():
    issues = compare_texts("ㅇ 총 502건 정비, 137명 참여\n", "ㅇ 총 502건 정비\n")
    assert any(i["rule"] == "numbers-lost" and "137" in str(i["values"]) for i in issues)

def test_cli_missing_args_exit2(tmp_path):
    import subprocess, sys as _sys
    r = subprocess.run([_sys.executable, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts/validate_hwpx.py"), "compare"], capture_output=True)
    assert r.returncode == 2

def test_numbers_mode_flags_unsourced(tmp_path):
    from validate_hwpx import numbers_check
    draft = "ㅇ 예산 349,850,000원, 참여 137명(23.7%)\n"
    rdir = tmp_path / "research"; rdir.mkdir()
    (rdir / "a.md").write_text("계약금액 349850000원 규모")   # 349,850,000 근거 있음(정규화 일치)
    issues = numbers_check(draft, rdir)
    vals = {v for i in issues for v in i["values"]}
    assert "137" in vals and "23.7" in vals          # 근거 없는 수치만 잔존
    assert not any("349" in v for v in vals)

def test_numbers_mode_clean(tmp_path):
    from validate_hwpx import numbers_check
    rdir = tmp_path / "research"; rdir.mkdir()
    (rdir / "a.jsonl").write_text('{"t":"137명 참여, 비율 23.70%"}')
    assert numbers_check("ㅇ 137명(23.7%)\n", rdir) == []

def test_numbers_mode_ignores_korean_dates(tmp_path):
    from validate_hwpx import numbers_check
    rdir = tmp_path / "research"; rdir.mkdir()
    draft = "ㅇ 시행 : '26.7월 / 기간 '26. 1. 13(화) ~ 1. 23(금) / 정비 502건\n"
    issues = numbers_check(draft, rdir)
    vals = {v for i in issues for v in i["values"]}
    assert "26.7" not in vals and "26.1" not in vals   # 날짜 표기는 수치 아님
    assert "502" in vals                                # 실수치는 검출 유지
