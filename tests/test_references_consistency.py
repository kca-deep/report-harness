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
