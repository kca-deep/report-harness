# tool-playbook — 출처 유형별 도구 선택표

> `report-research`(SKILL.md §1)의 참고 자료다. **강제 규칙이 아니다** — 조사 방법은 자유이며,
> 이 표는 "이런 출처면 이 도구가 잘 맞는다"는 매핑을 제시할 뿐이다. 강제되는 것은 SKILL.md §2의
> 산출 계약(경로·프론트매터·manifest)이지 여기서 어떤 도구를 썼는지가 아니다.

## 매핑표

| 출처 유형 | 우선 도구 | 비고 |
|---|---|---|
| 법령·판례·행정규칙 | MCP `korean-law` | `search_law`·`get_law_text`·`search_decisions`·`get_decision_text` 등. 조문·판결 원문 대조에 강함. |
| 공시·재무·기업정보 | MCP `opendart`(PlayMCP) | `search_disclosures`·`get_financial_account`·`get_company_info` 등. 상장사·공공기관 공시 확인용. |
| 한글 문서(hwp·hwpx·pdf·docx) 파싱 | MCP `kordoc` | `parse_document`(본문)·`parse_table`(표)·`parse_metadata`. 제공자료(모드 I) 처리에도 동일 도구. |
| 접근 차단·봇 방지 사이트(X/Twitter, Reddit, 네이버 블로그 등) | `insane-search` 스킬 | WebFetch가 402/403을 반환하거나 알려진 차단 플랫폼(X, Reddit, YouTube, GitHub, Medium, Substack, StackOverflow, 네이버 등)일 때. |
| 다출처 교차검증이 필요한 심층 주제 | `deep-research` 스킬 | 여러 출처를 팬아웃 검색 → 적대적 검증 → 인용 종합까지 한 번에 수행. 시간이 걸리므로 §5 시간 예산과 맞바꿔 판단. |
| 라이브러리·프레임워크·SDK 공식 문서 | MCP `Context7` | 버전별 최신 API 문서. 기술 스펙 확인용(보고서 주제가 기술 도입 검토일 때 유용). |
| YouTube 영상 내용 | `youtube-transcript` MCP | 자막 추출 후 텍스트로 인용. |
| 위 어느 것에도 해당 없는 일반 웹 조사 | `WebSearch` → `WebFetch` | 기본값. 검색으로 후보 URL 확보 후 본문 페치. |

## 환경 편차 흡수 규칙

**환경에 없는 MCP·스킬은 해당 행을 건너뛰고 일반 도구로 대체한다.** 이 플러그인은 위 도구들을
번들하지 않는다 — 사용자 환경에 이미 설치돼 있으면 활용하고, 없으면 표의 마지막 행(`WebSearch`
→ `WebFetch`)으로 강등해도 조사 자체는 계속 진행한다. 도구 부재로 조사를 중단하지 않는다.

대체가 발생하면 SKILL.md §6 종료 훅의 lessons 기록에 `[research]` 태그로 남긴다(예: "korean-law
미설치 — WebSearch로 법령 원문 검색 대체").

## 교차검증 원칙

핵심 주장(보고서 논지를 직접 지탱하는 사실·수치)은 **독립 출처 2개 이상**으로 대조한다.

- "독립"의 기준: 같은 1차 발행처를 재인용한 두 기사는 독립 출처가 아니다. 서로 다른 발행
  주체(정부 공표 vs 언론 보도, 또는 서로 다른 언론사)여야 한다.
- 출처 2개의 수치·사실이 일치하면 `confidence: 확정`. 하나만 확보됐거나 둘이 상충하면
  `confidence: 추정`으로 태깅하고, 상충 사실 자체를 산출물 본문에 명시한다(숨기지 않는다).
- 법령·공시처럼 원출처 자체가 유일하게 존재하는 유형(예: 특정 법 조문, 특정 기업의 특정 공시)은
  그 1차 출처 하나로 `확정` 처리해도 된다 — 교차검증은 "여러 매체의 진술을 대조"하는 데 의미가
  있지, 유일 원본을 억지로 두 번 찾는 절차가 아니다.
