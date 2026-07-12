---
name: macro-health-check
description: macro-dashboard의 db/macro.db 수집 상태를 점검합니다 (수집 누락·지연 감지). "오늘 수집 이상 없어?", "데이터 최신이야?" 같은 질문에 답하거나, 브리핑/리포트 작성 전에 데이터 신뢰도를 확인해야 할 때 사용하세요.
---

## 이 스킬이 하는 일

`scripts/macro_health_check.py`는 `config.py`에 정의된 전체 기대 티커 목록(FRED/ECOS/yfinance/장단기금리차)과 `db/macro.db`를 대조해, 다음 두 가지 "조용한 실패"를 찾아냅니다:

- **NEVER_COLLECTED**: 설정된 티커인데 DB에 행이 하나도 없음 (API 코드 오타, item_code 오류 등 구조적 문제 가능성 — 가장 심각)
- **STALE**: 행은 있지만 마지막 수집일이 기준(월별 지표 45일, 일별/거래일 지표 7일)보다 오래됨

이 두 상태는 `utils/validator.py`가 값을 걸러낸 경우와 API가 0건을 반환한 경우 모두 동일하게 나타나는 증상이라, 원인을 구분하지 않고 증상만으로 감지합니다.

## 실행 방법

**직접 실행할 때** (Bash 사용 가능한 환경 — 사람과 대화 중인 세션 등):
```bash
python scripts/macro_health_check.py
```
저장소 루트에서 실행해야 합니다 (`config.py`, `db/macro.db`를 상대 경로로 참조).

**이미 결과 파일이 있을 때** (예: CI에서 `scripts/macro_health_check.py > health_report.md`로 미리 생성해둔 경우): 스크립트를 다시 실행하지 말고 그 파일을 그대로 Read해서 해석하세요.

## 출력 해석

Markdown으로 `[NEVER_COLLECTED]`, `[STALE]`, `[OK]` 세 섹션이 출력됩니다. 문제가 전혀 없으면 "이상 없음, 총 N개 티커 정상" 한 줄만 나옵니다.

- `NEVER_COLLECTED`는 우선순위가 가장 높습니다 — config.py의 티커 코드/item_code가 맞는지, API가 정상 응답하는지부터 의심하세요.
- `STALE`은 일시적일 수 있습니다 (주말·공휴일로 인한 발표 지연, 배치 실행 실패 등) — 반복되는지 확인하는 게 중요합니다.

## 하지 말 것

이 스크립트는 읽기 전용입니다. DB나 코드 파일을 수정하지 않으며, 알림을 발송하지도 않습니다 — 결과를 어떻게 활용할지는 이 스킬을 호출한 에이전트/사람의 몫입니다.
