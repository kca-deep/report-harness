import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ROOT / "skills/report-pipeline/references"
# lint_md_profile.py 구현 룰 12종 (브리프 6종 + misplaced-marker + highlight-unpaired(R040)
# + 개선본 대조로 확정된 실무 관례 4종: caption-numbered·annex-crossref·lead-too-short·footnote-overflow)
RULES = ["inline-markdown", "non-bold-markup", "table-too-wide", "depth-exceeded",
         "bullet-overflow", "html-tag", "misplaced-marker", "highlight-unpaired",
         "caption-numbered", "annex-crossref", "lead-too-short", "footnote-overflow"]

def test_md_profile_mentions_all_lint_rules():
    text = (REF / "md-profile.md").read_text(encoding="utf-8")
    missing = [r for r in RULES if r not in text]
    assert missing == []

def test_hwpx_recipe_mentions_scripts():
    text = (REF / "hwpx-recipe.md").read_text(encoding="utf-8")
    for s in ["prep_report_md.py", "validate_hwpx.py", "check_image_size.py"]:
        assert s in text


def test_rules_seed_has_no_duplicate_ids():
    """배포 시드의 룰 번호는 유일해야 한다.

    운영 rules.md에 승격할 때 기존 번호를 확인하지 않아 R049·R050이 서로 다른 두 규칙에
    중복 부여된 사고가 있었다('26.8.4). 번호가 겹치면 rules 참조(SKILL.md·lint 주석·테스트)가
    어느 규칙을 가리키는지 결정 불가가 된다.
    """
    import re
    text = (REF / "rules-seed.md").read_text(encoding="utf-8")
    ids = re.findall(r"^- (R\d+)", text, re.M)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert dup == [], f"룰 번호 중복: {dup}"


def test_rules_seed_ids_are_contiguous():
    """룰 번호는 R001부터 빈틈없이 이어져야 한다 — 누락은 시드 동기화 실패 신호다."""
    import re
    text = (REF / "rules-seed.md").read_text(encoding="utf-8")
    nums = sorted(int(m[1:]) for m in re.findall(r"^- (R\d+)", text, re.M))
    missing = [n for n in range(1, nums[-1] + 1) if n not in nums]
    assert missing == [], f"시드에 누락된 룰 번호: {['R%03d' % n for n in missing]}"
