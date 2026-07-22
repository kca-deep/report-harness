import sys, pathlib
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
from prep_report_md import prep, prep_with_accounting, content_fingerprint, PrepError

def test_html_comment_removed():
    assert "비밀메모" not in prep("ㅇ 본문\n<!-- 비밀메모 -->\nㅇ 다음\n")

def test_hr_removed_but_blank_lines_preserved():   # 레거시 버그 회귀 테스트
    src = "＊ 각주: 설명\n\n---\n\n- 붙임 1. 목록\n"
    out = prep(src)
    assert "---" not in out
    assert "＊ 각주: 설명\n\n" in out          # 각주와 리스트 사이 빈 줄 생존
    assert "- 붙임 1. 목록" in out

def test_multiline_comment_rejected():
    src = "ㅇ 요지 <!-- 메모\nㅇ 본문줄\n-->\nㅇ 다음\n"
    with pytest.raises(PrepError):
        prep(src)

def test_setext_heading_rejected():
    with pytest.raises(PrepError):
        prep("분석 결과\n---\n본문\n")

def test_hr_with_blank_context_removed():
    out = prep("ㅇ A\n\n---\n\nㅇ B\n")
    assert "---" not in out and "ㅇ A" in out and "ㅇ B" in out

def test_singleline_comment_removed():
    assert "비밀" not in prep("ㅇ 본문\n<!-- 비밀 -->\nㅇ 다음\n")

def test_deletion_accounting():   # 삭제 문자수 회계 일치 (회귀 트립와이어)
    src = "ㅇ A\n<!-- x -->\n\n---\n\nㅇ B\n"
    out, deleted = prep_with_accounting(src)
    assert len(src) - len(out) == deleted

def test_footnote_normalized():
    assert "＊ 용어" in prep("\\* 용어: 정의\n")
