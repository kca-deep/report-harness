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
