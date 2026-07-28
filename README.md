# report-harness

기관보고서(개조식·hwpx) 작성 하네스. **자료조사 → 분석 → 초안 → hwpx 변환** 4단계를 하나의
파이프라인 스킬(`report-pipeline`)이 오케스트레이션하고, 게이트는 최대 3회(유형·수신·분량 Q&A /
아웃라인 승인 / 초안 승인+팩트체크)뿐이며 나머지 전 구간은 자동 진행한다. 시간 예산은 전 구간
30분(게이트 대기 제외), 매 게이트 피드백은 `lessons.jsonl`에 쌓여 규칙(`rules.md`)으로 복리
축적된다.

## 1. 설치

### 플러그인으로 설치 (배포판)

이 저장소는 Claude Code 플러그인 구조(`.claude-plugin/plugin.json` + `skills/` + `commands/`)를
따른다. 플러그인 설치 경로에 이 저장소를 등록하면 `skills/`·`commands/`가 자동으로 인식된다.

### 개발용 로컬 배포

플러그인 설치 없이 스킬·커맨드를 바로 검증하려면 직접 복사한다.

```bash
cp -R skills/* ~/.claude/skills/
cp -R commands ~/.claude/
```

- 기존에 동일 이름의 스킬·커맨드가 이미 있다면(예: 다른 출처의 `humanizer`) 덮어쓰지 말고
  개별 파일 단위로 병합할 것.
- 배포 전에는 반드시 `bash scripts/package_check.sh`로 배포 제외 항목·PII 잔존 여부를
  확인한다(§6).

## 2. 의존성

| 종류 | 이름 | 필수 여부 | 없을 때 |
|---|---|---|---|
| MCP | **kordoc** | **필수** | hwpx 생성·파싱·검증(§4 export)이 전부 불가 — 파이프라인은 `20_draft.md`(md) 인도로 **강등**되고, 인도 시 1줄로 고지한다. [kordoc 설치 안내](https://github.com/kordoc/kordoc-mcp) |
| MCP | korean-law | 선택 | 법령·판례 근거 조사 생략, 일반 검색(WebSearch)으로 대체 |
| MCP | opendart | 선택 | 공시·재무 데이터 조사 생략, 일반 검색으로 대체 |
| 스킬/도구 | insane-search | 선택 | 차단 사이트 우회 생략, 가능한 소스만 조사 |
| 스킬/도구 | deep-research | 선택 | 다출처 심층 조사 대신 WebSearch 1패스로 대체 |

`report-research` 스킬은 조사 "방법"을 강제하지 않는다 — 환경에 설치된 도구를 자유롭게 골라
쓰고, 없는 도구는 해당 행을 건너뛰고 대체 경로(위 표)로 흡수한다. 강제하는 것은 오직
**산출 계약**(`research/` 경로 규약 + `_manifest.jsonl`)뿐이다. 유일한 필수 의존성은
**kordoc**이며, hwp·hwpx·pdf·docx 파싱(모드 I)과 최종 hwpx 변환(export 단계)에 쓰인다.

## 3. 설정 파일 — `~/.claude/report-harness.json`

**설정 파일이 없어도 전 기능이 동작한다(설정 0 원칙)** — 첫 인도 시 안내를 1줄만 출력한다.
필요하면 아래 4키만 채운다.

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
| `state_dir` | `~/.claude/report-harness-state/` (자동 생성) | `rules.md`·`lessons.jsonl` 위치 |
| `knowledge_vault` | 없음 → vault 기능(사전지식 조회·적재 후보) 전부 생략 | 개인 지식 vault 루트(claudian 등) |
| `template_hwpx` | 없음 → kordoc 보고서 preset 기본 서식만 사용 | 기관 레터헤드·스타일 템플릿 병합용 |

### 사용자(bcchung81) 환경 설정 예시 — claudian 연동

claudian vault를 조사 산출물 저장소·사전지식 소스로 그대로 재사용하는 구성:

```json
{
  "reports_dir": "/Users/bcchung81/workspace/claudian/reports",
  "state_dir": "/Users/bcchung81/workspace/claudian/reports/_harness",
  "knowledge_vault": "/Users/bcchung81/workspace/claudian"
}
```

`template_hwpx`는 비워 둔다 — KCA 기본 양식 프로파일은 이미
`skills/report-pipeline/references/format-profile.kca.md`로 번들 시드되어 있어 별도 지정 없이
바로 적용된다.

## 4. 사용법

### 슬래시 커맨드 4종 (단계 단위 직접 진입)

| 커맨드 | 단계 | 설명 |
|---|---|---|
| `/report-research [주제]` | ① research | 신규조사·제공자료 적재·vault 사전지식 활용 |
| `/report-analyze [건명]` | ② analyze | 제공자료·조사 산출물 종합 분석 → `05_analysis.md` |
| `/report-draft [건명]` | ③ draft | Q&A 게이트⓪ → 아웃라인 게이트① → 초안 게이트② |
| `/report-export` | ④ export | 팩트체크∥회귀검사 → hwpx 변환 → `final/{제목}.hwpx` |

### 자연어 트리거 (전 구간 자동 연결)

커맨드 없이 자연어로 요청해도 `report-pipeline` 스킬이 필요한 단계를 자동으로 이어 붙인다.

- `"○○ 관련 최신 동향을 조사해서 보고서 만들어줘"` — research→analyze→draft→export 전 구간
- `"이어서 해줘"` — 마지막 작업폴더 상태(파일 구성)로 이어서 재개, 새 폴더 만들지 않음
- `"hwpx로 변환해줘"` — 게이트② 승인된 초안이 있으면 export 단계만 실행

작업폴더는 세션이 아니라 폴더 자체가 맥락을 기억한다 — 어느 단계에서 끊겨도 "이어서 해줘"로
재개 가능하다.

## 5. 배포 제외 항목

다음 두 디렉토리는 `.gitignore`로 배포 저장소에서 제외한다(로컬 파일은 유지, 추적에서만 제외):

- `form/` — 실보고서 원본 34건과 기관 양식 원본(hwp/hwpx) 일체, 12.6MB. 코퍼스 분석·실측
  재검증용 로컬 원자재이며 민감할 수 있어 배포하지 않는다. **파이프라인 런타임은 이 경로를
  참조하지 않는다**(코드 참조 0곳).
- `docs/analysis/` — 위 코퍼스에 대한 내부 분석 산출물.

런타임이 실제로 읽는 양식 자산은 `skills/report-pipeline/assets/` 아래 **번들 사본**이다
(`harness_config`의 `assets_dir`, 스킬 상대 경로 고정 — 배포 환경에서 `form/` 부재를 전제):

- `250609_표준보고서_KCA_문서양식.hwp` (64KB) — 양식 원본과 바이트 동일(md5 `88378b94…`)
- `도식Pool-경량.hwpx` (103KB) — 도식 Pool 원본(8.9MB)의 이미지 제거 경량본, 표 90개 유효

프레임워크·표 모음 원본은 번들 사본이 없으나, 추출 결과가 `references/table-pool.md`·
`diagram-pool.md`에 성문화돼 있어 런타임에는 원본이 필요 없다. 원본이 필요한 실측 재검증은
로컬 `form/`을 쓰고, 과거 추적분은 git 이력에서 복원한다(`git show 9312f63:'form/…'`).

## 6. 패키징 가드 (배포 전 필수 실행)

```bash
bash scripts/package_check.sh
```

- `git ls-files`로 `form/`·`docs/analysis/`가 여전히 추적 중인지 확인(추적 중이면 즉시 실패).
- `scripts/pii_scan.py`로 `skills/`·`commands/`만 스캔해 전화번호·이메일 잔존을 검사한다
  (스캔 루트를 배포 대상 디렉토리로 한정 — `tests/` 픽스처는 의도적 PII 예시를 포함하므로
  스캔 대상에서 제외).
- 모두 통과하면 `package check OK`를 출력한다.

## 7. 테스트

```bash
python3 -m pytest -q
```
