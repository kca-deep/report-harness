# hwpx-recipe — md→hwpx 변환 절차서

> 대상: `/report-export`(spec §6·§8-④)가 실행하는 변환 파이프라인. 입력은 게이트②에서 승인된
> `20_draft.md`(md-profile 준수, `md-profile.md` 참조). **원칙: "작성된 md 그대로" 변환** —
> 내용·구조·표·각주가 hwpx에 1:1로 재현되어야 한다(무손실). 초안 단계의 상시 lint 덕에 이
> 파이프라인은 "이미 통과한 입력"만 받는 것이 기본값이고, 왕복 QA는 확인 절차로 경량화된다.
>
> 결정론 스크립트(`prep_report_md.py`·`validate_hwpx.py`·`check_image_size.py`)는 stdlib-only
> 이고 MCP를 직접 호출할 수 없다 — hwpx 생성·되읽기는 kordoc MCP를 **모델이** 호출하고, 그
> 전후의 정규화·검증만 스크립트가 담당한다.

## 0. 사전조건

- 입력: `{work_dir}/20_draft.md` (게이트② 승인본, lint 통과 상태).
- `state_dir`(`harness_config.state_paths`)의 `rules.md`·`lessons.jsonl` 경로를 확보해 둔다 —
  실패 유형은 §6에서 여기 기록한다.
- 설정(`load_config`)의 `template_hwpx`가 지정돼 있으면 §2에서 서식 프로필을 병합한다.

## 1. prep 정규화 (무손실 정규화, 모호 입력 거부)

```
python3 skills/report-pipeline/scripts/prep_report_md.py \
    {work_dir}/20_draft.md -o {work_dir}/40_prepared.md
```

- `prep_report_md.py`는 의미 콘텐츠를 보존한다 — 단일행 HTML 주석 제거·문맥 확인된 구분선
  제거·각주 마커 전각 정규화만 수행하며, 삭제 문자수는 회계로 검증되고 모호한 입력(다중행
  주석·Setext 패턴)은 exit 2로 거부한다.
- **모호한 입력은 조용히 처리하지 않고 거부한다**(`PrepError`) — "모른다"를 명시적 실패로
  만드는 설계다. 대표 거부 사유:
  - `multiline-comment`: 여는 `<!--`와 닫는 `-->`가 다른 줄에 걸침(md-profile §2-3의
    "HTML 주석은 한 줄로만" 정책이 여기서 하드 실패로 강제된다).
  - `setext-ambiguous`: 구분선(`---`/`***`/`___`)의 앞뒤가 빈 줄이 아니어서 Setext 제목인지
    구분선인지 판정 불가.
  - `deletion-accounting-mismatch`: 삭제 문자 수 회계가 실제 삭제량과 어긋남(회귀 트립와이어).
- **exit 2**(`FATAL: {reason} at line {line} — 모호한 입력 거부`, stderr)면 **변환을 중단**하고
  사용자에게 사유·줄 번호를 그대로 보고한다. 20_draft.md를 수정해 원인을 제거한 뒤 이 단계부터
  재시도한다 — 다음 단계로 넘어가지 않는다.
- exit 0(`OK {work_dir}/40_prepared.md`)이면 §2로 진행.

## 2. 문서 생성 — kordoc `generate_document`

`template_hwpx`가 설정돼 있으면 먼저 서식 프로필을 추출해 병합 재료로 쓴다.

```
mcp__kordoc__extract_profile(
    hwpx_path="{template_hwpx}",
    output_path="{work_dir}/format-profile.json")
```

도식 마커(`도식: {패턴ID}`)가 본문에 있으면, `generate_document` 호출 전에 md 텍스트 단계에서
치환한다 — `diagram-pool.md` 판정표로 고른 패턴ID의 원형 표 구조를 도식 Pool 번들 hwpx에서
`parse_document`로 추출해 슬롯을 채운 뒤, GFM 표로 재구성해 `40_prepared.md`의 마커 자리에
병합한다(md-profile의 표 규격 안에서 조립).

```
mcp__kordoc__generate_document(
    markdown="{40_prepared.md 전문 — 도식 마커 치환 완료본}",
    output_path="{work_dir}/final/{제목}.hwpx",
    preset="보고서",
    font="myeongjo",
    body_pt=15,
    profile_path="{work_dir}/format-profile.json")   # template_hwpx 설정 시에만 전달
```

- `preset="보고서"`(1페이지 요약보고서 프리셋), `font="myeongjo"`(휴먼명조 계열),
  `body_pt=15` — spec §6-3 "명조 15pt" 확정값과 동일(해당 프리셋 기본값이기도 하지만 명시
  전달로 회귀를 막는다).
- `template_hwpx` 미설정 시 `profile_path`를 생략하면 kordoc 보고서 preset 기본 서식이
  적용된다(format-profile.kca.md가 번들 시드로 이미 반영된 상태).

## 3. 이미지 주입 — 규격 판정 → `patch_document`

본문의 이미지 마커(`도해: {id}`, 출처 캡션 병기)마다 후보 이미지를 규격 판정한다.

```
python3 skills/report-pipeline/scripts/check_image_size.py \
    research/images/{id}.png --max-w-mm 170 --max-h-mm 90 --dpi 96
```

- 출력 JSON: `{"w_mm":..,"h_mm":..,"fits":bool,"scale_to_fit":..}`.
- **exit 0**(규격 이내, `fits=true`): 주입 대상.
- **exit 1**(`fits=false`): `scale_to_fit` 비율로 축소해도 판독 가능하면 축소 재판정, 아니면
  차용 포기 — 텍스트 요약 + 출처 각주로 대체(마커 삭제).
- **exit 2**(포맷 오류 등): 해당 이미지는 건너뛰고 사유를 보고.

**통과분만** 주입한다. 방금 생성한 hwpx를 되읽어 이미지 마커 문단을 이미지 구문으로 치환한
편집본을 만들고 `patch_document`로 원본 서식(표·글꼴·도장칸)을 유지한 채 텍스트만 치환한다.

```
mcp__kordoc__patch_document(
    file_path="{work_dir}/final/{제목}.hwpx",
    edited_markdown="{parse_document로 얻은 마크다운에서 도해 마커 문단만
                      출처 캡션이 붙은 이미지로 치환한 전체 텍스트}",
    output_path="{work_dir}/final/{제목}.hwpx")
```

- `patch_document`는 블록 추가/삭제를 지원하지 않는다 — 이미지 마커 문단이 이미 존재하는
  자리에서만 치환이 성립한다(§7-1 배치 승인이 게이트①에서 이미 확정돼 있어야 하는 이유).
- 이미지가 없으면 이 단계는 생략하고 §4로 진행.

## 4. 검증 — 구조 검증 + 왕복 교차대조

### 4-1. 구조 검증

```
python3 skills/report-pipeline/scripts/validate_hwpx.py \
    structural {work_dir}/final/{제목}.hwpx
```

- zip 무결성(`testzip`) + 내부 xml 전체 파싱(`ET.fromstring`) 검사.
- exit 0(`{"errors": []}`): 구조 정상. exit 1: `errors` 배열에 손상 위치 나열 — §5로 이동
  (재변환 루프).

### 4-2. 왕복 되읽기

```
mcp__kordoc__parse_document(file_path="{work_dir}/final/{제목}.hwpx")
```

결과 마크다운을 모델이 `{work_dir}/40_roundtrip.md`로 저장한다(스크립트는 MCP를 직접 호출할
수 없으므로 이 저장은 모델 책임).

### 4-3. 내용 대조

compare의 src는 40_prepared.md — prep이 마크업(주석·구분선·각주 표기)을 바꾸므로 변환 입력과
동일본을 기준으로 대조해야 오탐이 없다. draft↔prepared 정합은 prep의 삭제 회계가 별도 보증한다.

```
python3 skills/report-pipeline/scripts/validate_hwpx.py \
    compare {work_dir}/40_prepared.md {work_dir}/40_roundtrip.md
```

- 대조 항목: □ 섹션 수·ㅇ/○ 요지 수·대시 상세 수·＊ 각주 수·표 개수·표 최대 열 수·수치 표본
  (콤마·소수 정규화 후 손실분), 그리고 되읽기 텍스트에 마크다운 잔재(헤딩·구분선·백틱·`**`·
  이탤릭·취소선(`~~..~~`)·서술 중 공백-하이픈 — 7종)가 남아있는지(AI 티 3중 장치 ③ — 변환기가 기호를 문자 그대로
  박아버리는 사고의 최종 검출선).
- exit 0(`{"issues": []}`): 일치. §7로 진행.
- exit 1: `issues` 배열에 `count-mismatch:{항목}` / `numbers-lost` / `markdown-leftover` 등
  판정 근거와 함께 나열 — §5로 이동.

## 5. 불일치 처리 — 재변환 루프 (최대 2회)

1. `validate_hwpx.py structural` 또는 `compare`가 exit 1을 내면, `issues`/`errors` 내용으로
   원인을 판정한다(예: 도식 표 병합 중 셀 텍스트 유실, 이미지 주입으로 인한 인접 문단 손상).
2. 원인에 대응하는 수정(마커 재구성·patch_document 재호출·generate_document 재실행)을 적용해
   §2~§4를 재실행한다.
3. 이 재변환 루프는 **최대 2회**까지 허용한다(최초 시도 포함 총 3회 시도).
4. 2회 재시도 후에도 불일치가 잔존하면 **조용한 변환 손실 금지** 원칙에 따라:
   - 잔존 불일치 전체 목록(`issues`/`errors`)을 사용자에게 명시 보고한다.
   - `20_draft.md`(항상 SSOT)를 그대로 인도한다 — hwpx 변환 실패가 md 인도를 막지 않는다.

## 6. lessons 기록

변환 과정에서 발생한 실패 유형(불일치·prep 거부·이미지 규격 초과 등)은 단계 종료 시
`state_dir/lessons.jsonl`에 `gate:"convert"`로 1줄 append한다(`gate`는
`research|analyze|outline|draft|factcheck|convert` 6값 enum 중 하나 — rules.md의 `[export]`
같은 단계 태그는 rules 파일 전용이며 feedback 문자열에 중복 삽입하지 않는다).

```json
{"date":"2026-07-22","case":"{work_dir 슬러그}","gate":"convert","feedback":"도식 표 치환 후 각주 수 불일치","fix":"슬롯 치환 순서 조정 후 재변환","promoted":false}
```

- 동일 유형이 2회 이상 반복 관찰되면 회고까지 기다리지 않고 그 자리에서 승격을 제안한다 —
  사용자 승인 시 `rules.md`에 `R0NN [export]`로 반영, `md-profile.md`의 금지 목록·
  `prep_report_md.py`의 거부 규칙으로 소급 반영할지 §5(md-profile.md)의 증보 절차를 따른다.

## 7. 인도

- `{work_dir}/final/{제목}.hwpx` + `{work_dir}/40_roundtrip.md`(왕복 대조 근거) +
  대조 결과 요약을 `40_qa.md`로 정리해 함께 인도한다.
- 1회 변환(재시도 0회)으로 통과한 경우가 표준 경로 — 초안 단계 lint가 이미 변환 가능
  프로파일만 통과시켰기 때문에 재변환 루프는 예외 처리다.

---

## 부록 — 스크립트 CLI 시그니처·exit 코드

| 스크립트 | 호출 | exit 0 | exit 1 | exit 2 |
|---|---|---|---|---|
| `prep_report_md.py` | `prep_report_md.py <src> -o <out>` | 정규화 성공, `<out>` 기록 | — (사용 안 함) | `PrepError`(모호한 입력 거부) |
| `validate_hwpx.py structural` | `validate_hwpx.py structural <path.hwpx>` | 구조 정상(`errors:[]`) | 구조 손상 발견(파일 미존재·zip 손상, `errors` 목록에 담겨 exit 1로 재변환 루프) | 인자 부족 |
| `validate_hwpx.py compare` | `validate_hwpx.py compare <src.md> <rt.md>` | 전항목 일치(`issues:[]`) | 불일치 발견 | 인자 부족(파일 접근 오류 시도 exit 2) |
| `check_image_size.py` | `check_image_size.py <img> [--max-w-mm 170] [--max-h-mm 90] [--dpi 96]` | 규격 이내(`fits:true`) | 규격 초과(`fits:false`) | 포맷 인식 실패 등 예외 |
