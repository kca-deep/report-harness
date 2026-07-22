#!/bin/bash
# 패키징 가드: 배포 제외 확인 + PII 스캔 (spec §12)
set -e
for banned in "form/보고서" "docs/analysis"; do
  if git ls-files | grep -q "^$banned/"; then echo "FATAL: $banned 이 추적됨 — 배포 금지 대상"; exit 1; fi
done
python3 scripts/pii_scan.py skills/ && python3 scripts/pii_scan.py commands/
echo "package check OK"
