# Changelog

## Unreleased (2026-07-28)
- R038: ※·＊ 단서/각주 뒤 ㅇ 복귀 전환 6pt 스페이서 추가 (postprocess TRANSITIONS cham→yo·star→yo)
- R039: 본문 괄호 13pt(R033)를 문단 전체 텍스트 기준 run 분할로 개정 — 문장 안 볼드로 run이 쪼개진 괄호도 처리(볼드 보존), cross_run_skipped 32→0
- R040: `==문구==` 노란 음영 하이라이트 도입 — md-profile §1-3 문법·lint `highlight-unpaired`(8종째)·postprocess `apply_highlight`(shadeColor=#FFFF00+볼드, 260331 실무본 실측)·compare `==` 잔존 검출
- R041: 머리말 배너(R030) 앵커 문단 lineSpacing 100% 강제 + subList textWidth 본문 폭 보정 — 도너 150%가 본문을 ≈4.6mm 밀던 제목표 상단 여백 실원인 정정, 기주입 문서 소급 수리(멱등)
- R042: 표 총 폭은 본문 폭 '미만' — 여유 283 hu(1.0mm) 확보. R036('이내')의 계열 정정으로, slack 0 축소가 같은 문단의 선행 요소 때문에 표를 다음 줄로 밀어 표 위에 15pt 빈 줄을 만들던 결함(사용자 6회 보고분의 정체)을 해소. `apply_fit_page_width`가 본문 폭 − 283으로 비례 축소하고, 그림 축소 시 scaMatrix e1/e5·rotationInfo centerX/Y 파생 캐시를 재계산(위생 동반 수정)
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

## 이력 백필 — R007~R037 (2026-07-22 ~ 07-28 승격분)

> 0.1.0 이후 승격된 규칙 31종의 변경 이력이 비어 있던 것을 사후 보전한 항목이다. 규칙 본문 정본은
> `skills/report-pipeline/references/rules-seed.md`이며 아래 요약은 그 원문을 압축한 것이다.
> 괄호 안은 해당 규칙이 승격된 커밋. 승격 당시 번호가 저장소 파일에 기록되지 않고 운영
> `state_dir/rules.md`에만 있던 규칙은 `번호 기록:` 으로 저장소 최초 기록 시점을 병기했다.

### 2026-07-22 — 실전 1건 시각 피드백 (`8be9607`·`7d88335`)
- R007: kordoc generate 입력은 리터럴 기호가 아니라 리스트 깊이 문법(`-`, 2칸, 4칸 = □/ㅇ/-)으로 변환해 전달 — 계층 평탄화 방지 (`8be9607`)
- R008: `generate_document` 호출 시 KCA 프로파일 파라미터 필수 — fonts(heading=HY헤드라인M·body=휴먼명조·ref=맑은고딕·table=맑은 고딕)·sizes(대15·참13·표12·제목20)·`bullet2=ᄋ`·body_title_box·line_spacing160 (`8be9607`, bullet2 실 enum 값 정정 `ef66021`)
- R009: 붙임은 3열 배너 표(`| 붙임 1 | | 제목 |`)로 작성하고 변환까지 유지 (`8be9607`)
- R010: 제목은 h1(`# `)로 변환 입력에 전달하고, 폰트 검증은 선언이 아니라 문단별 charPr '사용'을 확인 (`7d88335`)
- R011: ＊ 각주 문단은 생성 후 참고 charPr로 zip 패치 — kordoc은 ※만 인식 (`7d88335`)

### 2026-07-22 — postprocess 후처리 도입 (`7751904`~`d97591f`)
- R012: 발신 줄(`< 날짜, 부서 >`)은 `<right>` 래핑으로 우측 정렬 (`7751904`)
- R013: 계층 간격은 `postprocess_hwpx.py --spacing`이 양식 실측값(발신→□ 8pt·□→ㅇ 6pt·ㅇ→ㅇ 6pt·대시→ㅇ 6pt·ㅇ→- 6pt·-→＊ 3pt·블록 15pt·＊→표 10pt)으로 재현 (`7751904`; ㅇ→＊ 3pt 유추 `907fa8e`, ㅇ→ㅇ·대시→ㅇ 6pt 사용자 확정 `49d5e64`)
- R014: 간격 검증은 스페이서 개수가 아니라 **실효 간격**(스페이서+paraPr 여백 합산 pt) 기준 — `effective_gaps`가 리포트하고 `apply_zero_margins`가 콘텐츠 paraPr prev/next를 0화해 스페이서 단독 체계를 유지 (`3a5c2d8`, 번호 기록: `e32e05b`)
- R015: 표 정렬 규칙 도입 — 최초 형태는 '표 캡션·표 래퍼 문단 가운데 정렬'(`83ecab2`). '26.7.28 사용자 확정으로 **본문 콘텐츠 표 우측 정렬 + 캡션은 표 caption 내장(→R034)**으로 정정되고 구 규칙은 폐기, `apply_table_alignment`가 배정(제목 박스 CENTER·배너 표 좌측은 예외) (정정·번호 기록: `9312f63`)
- R016: ㅇ 괄호 리드는 볼드(`**(한 계)**`) — 코퍼스 관례 (`7e4fc17`)
- R017: 제목 박스 표는 무테두리·배경 보존 — 원본 borderFill 복제 변형으로 테두리만 NONE, 그라데이션 유지 (박제 `7e4fc17`, 구현 `0a53cbc`, 그라데이션 보존 재수정 `a45451f`, 번호 기록: `e32e05b`)
- R018: 발신 줄 글자 크기 12pt — 양식 바이너리 실측 확정 (박제 `7e4fc17`, 구현 `0a53cbc`, 번호 기록: `9312f63`)
- R019: 계층 시작은 원래 폰트의 리터럴 띄어쓰기(□0·ㅇ1·대시3·＊※5칸), 줄바꿈 하위는 자동 들여쓰기 — 내어쓰기 폭은 그 폰트 **글자 단위**로 산정(□ 1.5자·ㅇ 2자·대시 2.5자·＊※ 4자), `left=0`·`intent=-글자폭`. 표 셀 텍스트 CENTER, 표-문단 간격 캡션→표 3pt·표→※ 3pt·문단→캡션 6pt (박제 `7e4fc17` → 띄어쓰기 계층 전환 `a73bf51`·`8f39c81`(`--star-indent` 훅 폐기) → 내어쓰기 복원 `e77b213` → 글자 단위 병기 `019dd57` → `left=0`·`intent=-hang` 인코딩 정정 `da691b6`, 번호 기록: `e32e05b`)
- R020: 편집용지 여백 양식 강제 — 좌우 20·위 10·아래 15·머리말 15·꼬리말 10mm(`PAGE_MARGINS`), kordoc preset 위 15mm 결함 후처리 (`d97591f`)
- R021: compare `markdown-leftover` 중 볼드(`**`)·h1 제목·대시 선행공백 트림은 파서의 정상 재현 — hwpx XML 실물 검증(리터럴 기호 0건·charPr 실사용 확인)으로 무해 판정 후 진행 (**대응 커밋 없음** — 코드·문서 변경을 수반하지 않는 QA 판정 규칙, 번호 기록: `e32e05b`)

### 2026-07-24 — 20260724건 사용자 확정 (`3cf1611`~`848a9f6`)
- R022: 제목표 상단여백 미세 제거는 앵커 문단 줄간격 100% 치환 + 표 outMargin top 0. **상단 얇은 행(3.8pt)은 양식 원형의 배경 밴드이므로 행 삭제 금지** — 삭제 시 그라데이션 소실 회귀 (`3cf1611`, 재구현·회귀 복구 `2ad9e02`). 이후 조사에서 잔존 여백의 실체는 머리말 부재(→R030)·폭 초과(→R036)·slack 0(→R042)으로 계열 정정됨
- R023: 표 캡션·표 셀 글자는 12pt — 폰트는 유지하고 높이만 치환, 제목 박스 셀 제외 (`3cf1611`)
- R024: □ 절 제목은 항상 볼드 — `apply_dae_bold`가 dae 문단 run charPr에 bold 변형 배정 (`3cf1611`)
- R025: ☞ 등 결론 유도 기호는 ＊·※와 동일 계층 처리 — 선두 5칸 리터럴 띄어쓰기 + `left=0`·`intent=-4글자폭`, 인접 간격 3pt 준용 (R019 확장) (`3cf1611`)
- R026: 조사 기반 보고서는 본문=두괄식 결정·요지, 붙임=「검토 근거 상세」(2p 이내, R009 배너 표)로 분담 — style-guide §8 분담 원칙의 draft 단계 강제 (`2ad9e02`)
- R027: 붙임·참고 배너(3열 표)는 양식 참고 블록 정합 — 셀 글자 HY헤드라인M 16pt·앵커 문단 `pageBreakBefore=1`로 별도 페이지 시작·R023 12pt 강제 대상에서 제외 (`beaed03`). 셀 스타일 OLE 실측 증보(`0a6dc2b`) 후 **재실측 정정**(`848a9f6`): 라벨 셀 4변 SOLID 0.5mm #1B1760+채움 #2B2D63(남색)+흰 글자·행 28.3pt — HWP COLORREF는 `0x00BBGGRR`이라 hex 직독 시 R/B가 반전되며 최초 기록(적갈색)이 이 오류였음
- R028: 붙임은 각 1장 이내로 설계 — 계층형 문구는 렌더 기준 2줄 이내(휴먼명조 15pt ≈ 75자), 넘치는 상세는 표 전환·항목 분리·삭제로 압축 (`848a9f6`, 번호 기록: `e32e05b`)
- R029: ㅇ 항목이 (괄호) 리드로 시작하면 하위 대시는 (괄호) 리드를 쓰지 않는다 — 리드 중복 계층 방지 (`848a9f6`, 번호 기록: `e32e05b`)

### 2026-07-28 확정 — 제목표 상단여백 3·4차 조사 + 서식 정밀화 (일괄 커밋 `9312f63`)
- R030: 제목표 상단여백의 **확정 원인은 머리말(hp:header) 부재** — 편집용지 위 10mm+머리말 15mm=25mm가 통째로 빈 흰 띠로 남던 것. `apply_header_banner`(`--header-banner`·`--all`)가 실무본 이식 자산(`assets/kca-header-banner/`)을 id 재배정·manifest 등록과 함께 주입하고 hp:header 기존재 시 스킵(멱등). 편집용지 여백 축소로 대응 금지(양식 규격 위반). kordoc reflow 렌더는 머리말·hp:caption·pageBreakBefore를 그리지 않으므로 렌더 스크린샷으로 판정 금지
- R031: 본문 서술 중 용어 뒤 ＊ 표지는 **위첨자** — charPr에 `<hh:supscript/>`를 추가한 복제본으로 run 분리, 하단 `＊ 용어 : 설명` 각주 문단은 평문 유지(R011 참고 charPr 13pt). `apply_superscript_star`
- R032: 본문 계층 문단(□·ㅇ·대시)은 **양쪽 정렬(JUSTIFY)** — ＊·※ 각주·표 캡션·발신 줄은 기존 정렬 유지. `apply_body_justify`
- R033: 본문 서술 중 `(…)` 괄호 구간은 **13pt**(본문 15pt 대비 축소) — ㅇ 선두 괄호 리드(R016 라벨)는 라벨이므로 15pt 볼드 유지, 표 셀·＊※ 각주는 비대상. `apply_paren_small`
- R034: 표 캡션(`[ … ]`)은 표 바깥 문단이 아니라 `hp:tbl` 안 **`hp:caption`(side=TOP)에 내장** — 캡션 문단 CENTER+볼드, 캡션↔표 스페이서 빈 문단은 제거하고 전환 간격은 X→표로 승계(＊→표 10pt, ㅇ/대시/※→표 6pt). `apply_caption_embed`
- R035: 붙임·참고 배너 표(R027 3열)는 **좌측 정렬**(앵커 문단 LEFT) — R015 표 우측 정렬의 명시 예외
- R036: **표 총 폭(표 폭 + outMargin 좌우)은 본문 폭을 넘지 않는다** — 초과 시 표 폭·셀 폭·내부 그림을 같은 비율로 축소(`apply_fit_page_width`). 근거는 KCA 실보고서 12건 전수 실측에서 '머리말 배너 표 폭 == 본문 폭'이 예외 없이 성립한 것. 좌우 15mm 문서(260331)에서 이식한 배너가 좌우 20mm 문서에서 배너 10mm·제목박스 1mm 초과를 낳았고, 이것이 R022·R030 조사에서 못 찾은 상단 여백의 실제 원인이었다(여백 속성이 아니라 폭 초과)
- R037: 붙임·참고 배너 표의 **제목 셀(3번째) 문단은 양쪽 정렬** — 라벨·스페이서 셀은 CENTER 유지. `apply_annex_banner` ⑤가 배정하고 `apply_center_cell_text`는 배너 제목 셀을 제외(R023 12pt의 배너 셀 제외와 같은 패턴)

## 0.1.0 (2026-07-22)
- 최초 릴리스: report-pipeline(4단계 조합형 오케스트레이터)·report-research(산출 계약 조사)·humanizer(번들, MIT DaleSeo) 스킬 3종 + 슬래시 커맨드 4종
- 결정론 툴체인: harness_config / lint_md_profile(룰 7종) / prep_report_md(모호 입력 거부·삭제 회계) / validate_hwpx(structural·compare·numbers) / check_image_size / extract_format_profile + pii_scan 패키징 가드
- KCA 자산: style-guide(실보고서 34건 코퍼스)·format-profile 시드·도식 Pool 판정표·표 부품 카탈로그 26유형·rules 시드 R001~R006
- 검증: pytest 66개 + 설정 0 통합 스모크 8/8 (hwpx 1회 변환·왕복 QA 통과)
