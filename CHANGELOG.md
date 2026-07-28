# Changelog

## Unreleased (2026-07-28)
- R038: ※·＊ 단서/각주 뒤 ㅇ 복귀 전환 6pt 스페이서 추가 (postprocess TRANSITIONS cham→yo·star→yo)
- R039: 본문 괄호 13pt(R033)를 문단 전체 텍스트 기준 run 분할로 개정 — 문장 안 볼드로 run이 쪼개진 괄호도 처리(볼드 보존), cross_run_skipped 32→0
- R040: `==문구==` 노란 음영 하이라이트 도입 — md-profile §1-3 문법·lint `highlight-unpaired`(8종째)·postprocess `apply_highlight`(shadeColor=#FFFF00+볼드, 260331 실무본 실측)·compare `==` 잔존 검출
- R041: 머리말 배너(R030) 앵커 문단 lineSpacing 100% 강제 + subList textWidth 본문 폭 보정 — 도너 150%가 본문을 ≈4.6mm 밀던 제목표 상단 여백 실원인 정정, 기주입 문서 소급 수리(멱등)
- 동기화 부채 해소: installed↔repo (`inject_images.py`·`assets/kca-header-banner/` repo 누락분 복사)
- 테스트 118 → 142

## Unreleased (2026-07-29)
- 제거: `inject_images.py` — SKILL.md·commands·references·tests 어디서도 호출되지 않는 고아
  스크립트(참조 0곳, 131줄 전량 미실행). repo·installed 양쪽 삭제. 이미지 주입이 필요해지면
  `/tmp/_hwpx` 무조건 rmtree(:66-67,:144)와 재실행 시 zip 엔트리 중복(:124-130)을 고친 뒤
  파이프라인에 배선해 재도입한다 (이력: `git show 9312f63:skills/report-pipeline/scripts/inject_images.py`)
- 배포 제외 확대: `form/` 전체를 추적 해제(12.6MB, 배포 페이로드의 94.9%) — 런타임 참조 0곳이고
  양식 자산은 `assets/` 번들 사본(양식 hwp md5 동일·도식Pool 경량본)으로 충족. `.gitignore`·
  README §5·`package_check.sh` 가드 동기화. 로컬 원본은 유지, 과거 추적분은 git 이력에 보존
- **축적룰 전량 승계: `rules-seed.md` R001~R006 → R001~R042**. 그간 승격분 36종(R007~R042)이
  운영 `state_dir/rules.md`에만 있어 신규 설치자는 6종만 받던 격차를 해소 — 실제 운영 기준으로
  배포. 이후 승격은 운영 파일에 먼저 반영하고 배포 전 시드로 동기화한다
- 문서 정정: README `state_dir` 기본값 `~/.claude/report-harness-state/` → 실제값
  `{cwd}/.report-harness` (`harness_config.py:23`)

## 0.1.0 (2026-07-22)
- 최초 릴리스: report-pipeline(4단계 조합형 오케스트레이터)·report-research(산출 계약 조사)·humanizer(번들, MIT DaleSeo) 스킬 3종 + 슬래시 커맨드 4종
- 결정론 툴체인: harness_config / lint_md_profile(룰 7종) / prep_report_md(모호 입력 거부·삭제 회계) / validate_hwpx(structural·compare·numbers) / check_image_size / extract_format_profile + pii_scan 패키징 가드
- KCA 자산: style-guide(실보고서 34건 코퍼스)·format-profile 시드·도식 Pool 판정표·표 부품 카탈로그 26유형·rules 시드 R001~R006
- 검증: pytest 66개 + 설정 0 통합 스모크 8/8 (hwpx 1회 변환·왕복 QA 통과)
