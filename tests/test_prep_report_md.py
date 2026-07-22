import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
from prep_report_md import prep, content_fingerprint

def test_html_comment_removed():
    assert "비밀메모" not in prep("ㅇ 본문\n<!-- 비밀메모 -->\nㅇ 다음\n")

def test_hr_removed_but_blank_lines_preserved():   # 레거시 버그 회귀 테스트
    src = "＊ 각주: 설명\n\n---\n\n- 붕임 1. 목록\n"
    out = prep(src)
    assert "---" not in out
    assert "＊ 각주: 설명\n\n" in out          # 각주와 리스트 사이 빈 줄 생존
    assert "- 붕임 1. 목록" in out

def test_content_lossless():
    src = "□ 절\n ㅇ **요지** 문장\n<!-- 메모 -->\n---\n - 상세\n"
    assert content_fingerprint(prep(src)) == content_fingerprint(src)

def test_footnote_normalized():
    assert "＊ 용어" in prep("* 용어: 정의\n") or "＊" in prep("\\* 용어: 정의\n")
