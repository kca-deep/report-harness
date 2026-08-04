import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
from lint_md_profile import lint_text

def rules(violations):
    return {v["rule"] for v in violations}

def test_clean_gaejosik_passes():
    # 괄호 리드는 3음절 이상 구체 명사구(R051) — 표 헤더의 2음절 벌려쓰기(`구 분`)는 계속 합법.
    text = ("□ 추진 배경\n"
            " ㅇ (추진 목적) AI 활용 **격차 해소**를 위한 환경 조성\n"
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

def test_bullet_overflow_under_one_yo():   # R045: 3개째부터 위반
    text = "ㅇ 요지\n" + "".join(f"   - 상세{i}\n" for i in range(3))
    assert "bullet-overflow" in rules(lint_text(text))

def test_two_bullets_allowed_under_one_yo():   # R045: 2개까지는 합법
    text = "ㅇ 요지\n   - 상세1\n   - 상세2\n"
    assert "bullet-overflow" not in rules(lint_text(text))

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

def test_bullet_run_resets_at_section():   # □ 경계에서 카운터 리셋 (R045 상한 2개 기준)
    text = ("ㅇ A\n   - a\n   - b\n"
            "□ 새 절\n   - c\n   - d\n")
    assert "bullet-overflow" not in rules(lint_text(text))

def test_chevron_label_not_html():         # 코퍼스 관례: < > 영문 혼용 라벨
    assert "html-tag" not in rules(lint_text("ㅇ <AI 활용 방안> 관련 논의\n"))

# ── 개선본 대조로 확정된 실무 관례 (R051~R053·R056) ──────────────────────────

def test_caption_numbered_detected():      # R056: 캡션에 표 일련번호 금지
    assert "caption-numbered" in rules(lint_text("[ 표1. 추진 총괄 요약 ]\n"))

def test_caption_descriptive_ok():         # 내용 서술형 캡션은 합법
    assert lint_text("[ 월별 바이브코딩 교육 진행 ]\n") == []

def test_annex_defer_detected():           # R053: 괄호로 붙임에 설명을 미루는 표기
    text = "ㅇ (초기 설계) 3레이어 하이브리드 구조(상세 붙임1 참조)\n"
    assert "annex-crossref" in rules(lint_text(text))

def test_annex_closing_note_ok():          # 맺음의 ※ 참조는 코퍼스 합법 관례
    assert "annex-crossref" not in rules(lint_text("※ 세부내용은 붙임 참조\n"))

def test_lead_two_syllable_detected():     # R051: 2음절 괄호 리드 (벌려쓴 형태·붙인 형태 모두)
    assert "lead-too-short" in rules(lint_text("ㅇ **(품 질)** 오류율 0%\n"))
    assert "lead-too-short" in rules(lint_text("ㅇ **(배포)** 배포 완료\n"))

def test_lead_specific_noun_ok():          # 3음절 이상 구체 명사구는 합법
    assert lint_text("ㅇ **(서비스 품질)** 오류율 0%\n") == []

def test_footnote_overflow_detected():     # R052: 용어 각주 4개 초과
    text = "".join(f"＊ 용어{i} : 설명\n" for i in range(5))
    assert "footnote-overflow" in rules(lint_text(text))

def test_footnote_within_limit_ok():
    text = "".join(f"＊ 용어{i} : 설명\n" for i in range(4))
    assert "footnote-overflow" not in rules(lint_text(text))
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

def test_grade_label_not_html():           # <A 등급> 등 단일문자+공백 라벨은 HTML 아님
    for s in ["ㅇ <A 등급> 사업 검토\n", "ㅇ <B 안> 채택\n", "ㅇ <I 유형> 분류\n", "ㅇ <P 형> 지정\n"]:
        assert "html-tag" not in rules(lint_text(s))

def test_second_box_on_valid_line_detected():  # 선두 □ 합법 + 같은 줄 두 번째 □ 검출
    assert "misplaced-marker" in rules(lint_text("□ 첫 항목: 세부는 별도 □ 서식 참조\n"))

def test_highlight_marker_allowed():       # R040: ==특히 강조== 하이라이트 문법 합법
    assert lint_text("ㅇ 핵심은 ==특히 강조== 사항\n") == []
    assert lint_text("ㅇ **볼드**와 ==하이라이트== 병용\n") == []

def test_highlight_unpaired_detected():    # 짝 안 맞는 == 는 잔존 위험 — 위반
    assert "highlight-unpaired" in rules(lint_text("ㅇ 핵심은 ==특히 강조 사항\n"))
