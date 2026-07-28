#!/bin/bash
# 패키징 가드: 배포 제외 확인 + PII 스캔 (spec §12)
set -e
for banned in "form" "docs/analysis"; do
  # core.quotepath=false: 한글 경로가 8진 이스케이프로 출력되어 grep이 놓치는 것 방지
  if git -c core.quotepath=false ls-files | grep -q "^$banned/"; then echo "FATAL: $banned 이 추적됨 — 배포 금지 대상"; exit 1; fi
done
python3 scripts/pii_scan.py skills/ && python3 scripts/pii_scan.py commands/
echo "package check OK"
