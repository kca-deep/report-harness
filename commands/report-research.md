---
description: "기관보고서 자료조사 — 신규조사·제공자료 적재·vault 사전지식 활용 (report-pipeline ①단계)"
---

report-research 스킬을 직접 로드하고 **① research 단계**를 실행하라. 작업폴더가 없으면 생성하고, 있으면 기존 폴더를 재사용한다(이어가기 지원). $ARGUMENTS가 있으면 조사 주제로 사용하고, 없으면 "어떤 주제를 조사할까요?"만 묻는다. 산출은 `research/provided/` (제공자료), `research/fetched/{주제슬러그}/` (신규조사) 경로 규약을 따르며 `_manifest.jsonl` 메타데이터를 필수로 포함한다.
