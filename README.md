# report-harness

**"이 주제로 보고서 써줘" 한 마디로 기관보고서 hwpx 파일까지 만드는 Claude Code 플러그인.**

자료조사 → 분석 → 초안(개조식) → hwpx 변환 4단계를 하나의 파이프라인이 알아서 이어 붙인다.
사람이 개입하는 지점은 최대 3번뿐이고 나머지는 자동으로 흘러간다. 매번 받은 피드백은
`lessons.jsonl`에 쌓여 규칙(`rules.md`)으로 승격되므로, 쓰면 쓸수록 같은 지적을 덜 받는다.

산출물은 한글(HWP) 양식에 맞춘 `.hwpx` 파일이다 — 글머리 기호 계층(□·ㅇ·-), 폰트·크기,
줄간격, 표 정렬, 붙임 배너까지 기관 양식 실측값으로 맞춰서 나온다.

---

## 1. 30초 시작

```
/plugin marketplace add kca-deep/report-harness
/plugin install report-harness@report-harness
```

설치하면 스킬 3종·슬래시 커맨드 4종·MCP 2종이 함께 붙는다. 그다음 아무 말이나 하면 된다.

```
"AI 활용 성과측정 체계 개선방안으로 보고서 써줘"
```

**설정 파일은 안 만들어도 된다.** 전부 기본값으로 동작한다(§5).

> **한 가지만 확인**: hwpx 변환은 `kordoc` MCP가 담당한다. 함께 설치되지만 첫 실행 시
> `npx`가 패키지를 내려받으므로 네트워크가 필요하다. kordoc이 없으면 마크다운 초안까지만
> 만들어지고 그 사실을 1줄로 알려준다.

---

## 2. 무엇을 해주나 — 4단계와 게이트 3번

| 단계 | 하는 일 | 산출물 |
|---|---|---|
| ① research | 자료조사. 제공자료 적재·신규조사·vault 사전지식 조회 | `research/` + `_manifest.jsonl` |
| ② analyze | 조사 결과 종합 분석 | `05_analysis.md` |
| ③ draft | 개조식 초안 작성 | `20_draft.md` |
| ④ export | 팩트체크 ∥ 회귀검사 → 양식 정합 변환 | `final/{제목}.hwpx` + `40_qa.md` |

멈춰 서서 물어보는 지점은 셋뿐이다.

- **게이트⓪** — 보고서 유형·수신자·분량 확인 (③ 시작 시)
- **게이트①** — 아웃라인 승인
- **게이트②** — 초안 승인 + 팩트체크 범위 선택

**작업폴더가 맥락을 기억한다.** 세션이 끊겨도 `"이어서 해줘"` 한 마디면 폴더 상태를 읽고
그 지점부터 재개한다. 새 폴더를 만들지 않는다.

---

## 3. 사용법

### 자연어로 (권장)

```
"○○ 관련 최신 동향 조사해서 보고서 만들어줘"   → 4단계 전 구간
"이어서 해줘"                                  → 마지막 작업폴더에서 재개
"hwpx로 변환해줘"                              → 승인된 초안이 있으면 ④단계만
```

### 슬래시 커맨드로 (단계 단위 직접 진입)

| 커맨드 | 단계 | 언제 쓰나 |
|---|---|---|
| `/report-research [주제]` | ① | 조사부터 시작 |
| `/report-analyze [건명]` | ② | 자료가 이미 있을 때 |
| `/report-draft [건명]` | ③ | 분석까지 끝났을 때 |
| `/report-export` | ④ | 초안만 hwpx로 바꿀 때 |

4단계를 다 거칠 필요는 없다. 가진 재료에 맞는 단계로 바로 들어가면 된다.

---

## 4. 스킬 구조

플러그인 하나에 스킬 3종이 들어 있다. **`report-pipeline`이 지휘자**이고 나머지는 필요할 때
불려 나간다.

```
report-harness/
├── .claude-plugin/
│   ├── plugin.json          플러그인 정의
│   └── marketplace.json     이 저장소를 마켓플레이스로 등록
├── .mcp.json                번들 MCP 2종 (kordoc·korean-law)
│
├── skills/
│   ├── report-pipeline/     ★ 오케스트레이터 — 4단계 전체를 지휘
│   │   ├── SKILL.md         단계 흐름·게이트·시간예산 정의
│   │   ├── references/      ← 판단 기준 (LLM이 읽는 문서)
│   │   │   ├── style-guide.md        실보고서 34건에서 뽑은 문체·구성 관례
│   │   │   ├── md-profile.md         변환 가능한 마크다운 규격 + 린트 룰 8종
│   │   │   ├── format-profile.kca.md 기관 양식 실측 프로파일(폰트·크기·여백)
│   │   │   ├── hwpx-recipe.md        hwpx 변환 절차서
│   │   │   ├── rules-seed.md         회귀 방지 규칙 R001~R042 (복리축적 시드)
│   │   │   ├── diagram-pool.md       표 기반 도식 패턴 카탈로그
│   │   │   └── table-pool.md         표 부품 카탈로그
│   │   ├── scripts/         ← 결정론 도구 (기계가 실행, LLM 판단 배제)
│   │   │   ├── harness_config.py     설정 해석·기본값 폴백
│   │   │   ├── lint_md_profile.py    초안 규격 검사 (룰 8종)
│   │   │   ├── prep_report_md.py     변환 전 정규화 (무손실 보장)
│   │   │   ├── postprocess_hwpx.py   ★ 양식 정합 후처리 (R011~R042)
│   │   │   ├── validate_hwpx.py      구조·대조·수치 검증
│   │   │   ├── check_image_size.py   이미지 규격 판정
│   │   │   └── extract_format_profile.py 양식 파일에서 프로파일 추출
│   │   └── assets/          기관 양식 원본·도식 Pool·머리말 배너 자산
│   │
│   ├── report-research/     ① 자료조사 — 방법은 자유, 산출 계약만 강제
│   │   ├── SKILL.md
│   │   └── references/tool-playbook.md  어떤 도구를 언제 쓰나
│   │
│   └── humanizer/           초안 윤문 — AI 문체 흔적 제거 (MIT, DaleSeo)
│
└── commands/                슬래시 커맨드 4종 (단계별 진입점)
```

### 설계 원칙 셋

**1. 판단은 문서로, 실행은 스크립트로.** `references/`는 LLM이 읽고 판단하는 기준이고,
`scripts/`는 판단이 끼어들면 안 되는 결정론 작업(정규화·린트·검증·후처리)이다. 양식 정합처럼
"매번 똑같아야 하는 것"은 전부 스크립트로 내려서 LLM 편차를 없앴다.

**2. 조사는 방법을 강제하지 않는다.** `report-research`가 요구하는 건 오직 산출 계약
(`research/` 경로 규약 + `_manifest.jsonl`)뿐이다. 환경에 있는 도구를 골라 쓰고, 없는 도구는
건너뛰고 대체 경로로 흡수한다. 그래서 도구가 하나도 없어도 파이프라인이 멈추지 않는다.

**3. 규칙은 복리로 쌓인다.** 게이트에서 받은 지적이 `lessons.jsonl`에 기록되고, 반복되거나
사용자가 확정하면 `rules.md`에 `R0NN`으로 승격된다. 다음 보고서부터 그 규칙이 회귀검사로
자동 적용된다. 현재 **R001~R042**가 시드로 들어 있다.

---

## 5. 준비물

### 함께 설치되는 것 (할 일 없음)

| | 이름 | 역할 |
|---|---|---|
| 스킬 | `report-pipeline` · `report-research` · `humanizer` | 플러그인에 포함 |
| MCP | **`kordoc`** | **필수** — hwp·hwpx·pdf·docx 파싱, hwpx 생성·검증. API 키 불필요 |
| MCP | `korean-law` | 선택 — 법령·판례 근거 조사. **아래 키 발급 필요** |

### 키를 직접 발급받아야 하는 것 — `korean-law`

법령 조사를 쓰려면 **법제처 Open API 인증키(OC)** 가 필요하다. 무료이고 1분이면 된다.

1. [법제처 Open API 신청 페이지](https://open.law.go.kr/LSO/openApi/guideList.do) 접속
2. 회원가입 → 로그인 → **"Open API 사용 신청"**
3. 발급받은 **인증키(OC)** 를 환경변수로 등록

```bash
# ~/.zshrc 또는 ~/.bashrc 에 추가
export LAW_OC="발급받은_인증키"
```

**키가 없어도 나머지는 전부 정상 동작한다.** `korean-law` 서버만 연결에 실패하고, 법령 조사가
필요한 대목은 일반 웹 검색으로 대체된다.

### 있으면 좋은 것 (없어도 무방)

- **`insane-search`** — X/Reddit/네이버처럼 봇 차단이 걸린 사이트에서 자료를 가져올 때.
  없으면 접근 가능한 소스만 조사한다. (별도 마켓플레이스 플러그인)
- **개인 지식 vault** — Obsidian 등. `knowledge_vault`를 설정하면 조사 결과를 축적하고
  다음 보고서에서 사전지식으로 재활용한다. 설정하지 않으면 vault 기능만 생략된다.

---

## 6. 설정 (선택)

**설정 파일이 없어도 전 기능이 동작한다.** 첫 인도 시 안내를 1줄만 출력한다. 필요하면
`~/.claude/report-harness.json`에 아래 4키만 채운다.

```json
{
  "reports_dir":     "/path/to/reports",
  "state_dir":       "/path/to/state",
  "knowledge_vault": "/path/to/obsidian-vault",
  "template_hwpx":   "/path/to/기관보고양식.hwpx"
}
```

| 키 | 없을 때 기본값 | 역할 |
|---|---|---|
| `reports_dir` | `{cwd}/reports` | 건별 작업폴더 루트(`{reports_dir}/{YYYYMMDD}/{HHMM}_{슬러그}/`) |
| `state_dir` | `{cwd}/.report-harness` (자동 생성) | `rules.md`·`lessons.jsonl` 위치. 첫 실행 시 `rules-seed.md`(R001~R042)를 복사 |
| `knowledge_vault` | 없음 → vault 기능(사전지식 조회·적재) 생략 | 개인 지식 vault 루트 |
| `template_hwpx` | 없음 → 번들 기본 서식 사용 | 기관 레터헤드·스타일 템플릿 병합용 |

`template_hwpx`는 대개 비워 둔다 — KCA 기본 양식 프로파일이
`references/format-profile.kca.md`로 번들 시드되어 별도 지정 없이 적용된다.

### vault 연동 예시

조사 산출물 저장소와 사전지식 소스를 같은 vault로 묶는 구성:

```json
{
  "reports_dir": "~/workspace/my-vault/reports",
  "state_dir": "~/workspace/my-vault/reports/_harness",
  "knowledge_vault": "~/workspace/my-vault"
}
```

---

## 부록 — 개발자용

### 로컬에서 직접 검증

플러그인 설치 없이 스킬·커맨드를 바로 시험하려면 복사한다.

```bash
cp -R skills/* ~/.claude/skills/
cp -R commands ~/.claude/
```

동일 이름 스킬이 이미 있으면(예: 다른 출처의 `humanizer`) 덮어쓰지 말고 파일 단위로 병합할 것.

### 배포 제외 항목

다음은 `.gitignore`로 배포 저장소에서 제외한다(로컬 파일은 유지, 추적에서만 제외).

- `form/` — 실보고서·기관 양식 원본(hwp/hwpx) 12.6MB. 코퍼스 분석·실측 재검증용 로컬
  원자재이며 민감할 수 있어 배포하지 않는다. **런타임은 이 경로를 참조하지 않는다**(참조 0곳).
- `docs/analysis/` — 위 코퍼스에 대한 내부 분석 산출물.

런타임이 읽는 양식 자산은 `skills/report-pipeline/assets/` 아래 번들 사본이다
(`harness_config`의 `assets_dir`, 스킬 상대 경로 고정 — 배포 환경에서 `form/` 부재를 전제).

- `250609_표준보고서_KCA_문서양식.hwp` (64KB) — 양식 원본과 바이트 동일(md5 `88378b94…`)
- `도식Pool-경량.hwpx` (103KB) — 도식 Pool 원본(8.9MB)의 이미지 제거 경량본, 표 90개 유효

프레임워크·표 모음 원본은 번들 사본이 없으나, 추출 결과가 `table-pool.md`·`diagram-pool.md`에
성문화돼 있어 런타임에는 원본이 필요 없다.

### 패키징 가드 (배포 전 필수)

```bash
bash scripts/package_check.sh
```

- `git ls-files`로 `form/`·`docs/analysis/`가 여전히 추적 중인지 확인(추적 중이면 즉시 실패).
- `scripts/pii_scan.py`로 `skills/`·`commands/`만 스캔해 전화번호·이메일 잔존을 검사한다
  (`tests/` 픽스처는 의도적 PII 예시를 포함하므로 스캔 대상에서 제외).
- 모두 통과하면 `package check OK`를 출력한다.

### 테스트

```bash
python3 -m pytest -q
```

참조 문서 간 정합성(`test_references_consistency.py`), 플러그인·마켓플레이스 매니페스트 구조와
버전 일치(`test_plugin_structure.py`), 후처리 규칙 회귀(`test_postprocess_hwpx.py`)를 포함한다.
