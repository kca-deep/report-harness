import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
from lint_md_profile import lint_text

def rules(violations):
    return {v["rule"] for v in violations}

def test_clean_gaejosik_passes():
    text = ("□ 추진 배경\n"
            " ㅇ (목 적) AI 활용 **격차 해소**를 위한 환경 조성\n"
            "   - ChatGPT Team 6개 계정 구독(약 3.2백만원/연) 지원\n"
            "※ 세부내용은 붙임 참조\n"
            "| 구 분 | 내용 |\n| --- | --- |\n| A | B |\n")
    assert lint_text(text) == []

def test_inline_dash_and_star_detected():  # R001: 서술 중 - * 잔재
    text = "ㅇ 조사 결과 - 세 가지로 요약되며 *중요* 항목은 다음과 같음\n"
    assert {"inline-markdown", "non-bold-markup"} <= rules(lint_text(text))

def test_inline_backtick_and_heading():
    assert "inline-markdown" in rules(lint_text("ㅇ 명령은 `run` 사용\n"))
    assert "inline-markdown" in rules(lint_text("# 제목처럼 쓴 마크다운\n"))

def test_bold_is_allowed():
    assert lint_text("ㅇ **핵심 명사구** 강조는 허용\n") == []

def test_table_over_6_cols():
    text = "| a | b | c | d | e | f | g |\n| - | - | - | - | - | - | - |\n"
    assert "table-too-wide" in rules(lint_text(text))

def test_bullet_overflow_under_one_yo():
    text = "ㅇ 요지\n" + "".join(f"   - 상세{i}\n" for i in range(6))
    assert "bullet-overflow" in rules(lint_text(text))

def test_html_tag():
    assert "html-tag" in rules(lint_text("ㅇ 내용 <br> 줄바꿈\n"))

def test_depth_exceeded_on_deep_nesting():
    text = ("□ 절\n"
            " ㅇ 요지\n"
            "   - 상세\n"
            "      - 5단 중첩 세부\n")
    assert "depth-exceeded" in rules(lint_text(text))

def test_depth_ok_within_4_levels():
    text = "□ 절\n ㅇ 요지\n   - 상세\n※ 단서\n＊ 각주\n"
    assert lint_text(text) == []

def test_bullet_run_resets_at_section():   # □ 경계에서 카운터 리셋
    text = ("ㅇ A\n   - a\n   - b\n   - c\n"
            "□ 새 절\n   - d\n   - e\n   - f\n")
    assert "bullet-overflow" not in rules(lint_text(text))

def test_chevron_label_not_html():         # 코퍼스 관례: < > 영문 혼용 라벨
    assert "html-tag" not in rules(lint_text("ㅇ <AI 활용 방안> 관련 논의\n"))
    assert "html-tag" in rules(lint_text("ㅇ 내용 <br> 줄바꿈\n"))
    assert "html-tag" in rules(lint_text("<table><tr><td>x</td></tr></table>\n"))

def test_nested_dash_is_depth_violation(): # 대시 중첩 = 위반 (들여쓰기 폭 무관)
    text = " ㅇ 요지\n  - 상세\n    - 중첩 세부\n"
    assert "depth-exceeded" in rules(lint_text(text))

def test_same_level_dashes_ok_any_indent():# 동일 레벨 대시는 들여쓰기 폭 무관 정상
    text = " ㅇ 요지\n     - 상세1\n     - 상세2\n"
    assert "depth-exceeded" not in rules(lint_text(text))

def test_triple_star_detected():           # ***볼드이탤릭*** 우회 차단
    assert "non-bold-markup" in rules(lint_text("ㅇ 이는 ***매우 중요***한 사안임\n"))

def test_midtext_box_symbol_detected():    # 문장 중간 □ 검출
    assert "misplaced-marker" in rules(lint_text("ㅇ 문장 중간에 □ 표기가 있는 경우\n"))

def test_inline_trailing_note_allowed():   # ※ 인라인 후행 참조는 코퍼스 합법 패턴
    assert lint_text("ㅇ 측정 3원칙 적용 ※ 등급별 산식은 붙임 2\n") == []
