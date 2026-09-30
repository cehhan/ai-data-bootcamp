---
name: build-dashboard
description: data/의 유저 이벤트 로그(user_events.csv)를 집계·분석해, templates/reference.html과 동일한 퀄리티의 PM 지표 위계·원인 분석 대시보드를 output/에 생성하는 스킬. "대시보드 만들어줘", "/build-dashboard" 시 사용.
argument-hint: "[CSV 경로 — 생략 시 data/user_events.csv]"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Bash
---

# build-dashboard — PM 지표 대시보드 자동 생성

수강생이 이 명령 하나만 치면, 강사 퀄리티의 지표 위계 대시보드가 자기 데이터로 나온다.
**반드시 아래 5단계를 순서대로 수행한다. 단계를 건너뛰지 않는다.**

## STEP 1 — 데이터 읽기 (EDA)
- 인자로 받은 CSV(없으면 `data/user_events.csv`)를 로드. **유저 이벤트 로그이므로 행을 다 읽지 말고 python(pandas)으로 집계**한다 — 코호트 리텐션·RFM·이탈 시점/플랜·비율 KPI를 CLAUDE.md의 집계 매핑대로 계산.
- 컬럼·행 수·지표 목록·기간을 한 줄로 요약해 사용자에게 보여준다.
- 필수 컬럼 확인: `user_id, event_date, event, plan, segment`. **없으면 진행하지 말고 사용자에게 알린다.**
- `event` 값 확인: `signup · login · trial_start · payment · cancel · search_fail`.
  - 컬럼명이 다르면 가장 가까운 것에 매핑하고, 매핑 결과를 알려준다.
- 어떤 지표가 시계열(주차별)인지, 어떤 행이 세그먼트/사유 스냅샷인지 구분한다.

## STEP 2 — 지표 계산 (실제 숫자)
- `CLAUDE.md`의 정의대로 계산/집계한다:
  - **지표 위계 값**: 최신 주차의 재결제율·구독/체험 전환율·리텐션 + 전주 대비 `%p` 델타 → `treeData`/`metricsTable`.
  - **구독자 증감 비율** = (신규 + 복귀) / 이탈. `< 1`이면 위험 플래그.
  - **세그먼트별 집계**: RFM 6세그먼트 비중 → `rfmData`. 비중 내림차순.
  - **원인 기여도**: 이탈 사유 비중 + `verified` 플래그 → `causeData`.
  - **시계열**: 주차별 좌절 경험률·이탈률 → `frustData`, 이탈 시점/플랜 분포 → `timingData`/`planData`.
- 계산은 Bash(python)로 실제 수행하고, 결과 수치를 표로 한 번 보여준다. **추정·반올림 임의값 금지.**

## STEP 3 — 레퍼런스 구조 흡수
- `templates/reference.html`을 **반드시 Read** 한다.
- HTML 골격(사이드바, KPI 카드 6개, STEP 1~4 섹션, 트리/Pulse/트리맵/표), CSS 토큰, chart.js·SVG 초기화 패턴을 파악한다.
- 각 const 배열(`treeData` 513줄 / `frustData` 566줄 / `timingData` 617줄 / `planData` 630줄 / `rfmData` 644줄 / `causeData` 746줄 / `metricsTable` 802줄)의 **필드명·형식**을 정확히 확인한다.
- 이 구조를 그대로 재사용한다 — 새로 디자인하지 않는다.

## STEP 4 — 데이터 주입해서 렌더
- 레퍼런스 구조 위에 STEP 2의 **실제 계산값**을 채워 `output/pm_dashboard.html` 생성.
- const 배열의 값만 정규식으로 교체 — **필드명/형식/JS 로직은 절대 건드리지 않는다** (안 그러면 차트 깨짐).
- KPI 카드 6개 숫자, 트리 델타, Pulse 분해(신규/복귀/이탈), 세그먼트 비중, 사유 비중, 테이블을 모두 새 값으로.
- 제목/기준 날짜를 데이터 기간으로 갱신. KPI 수치는 검정 고정(증감 비율 같은 즉각 위험만 빨강 허용).
- `CLAUDE.md`의 금지 항목(한쪽 border, 수치 색 남용, 장식, 필드명 변경)을 위반하지 않았는지 자체 점검.

## STEP 5 — 전달
- 저장 경로의 **절대경로 file:// 링크**를 안내한다.
- "이번 데이터 기준 최우선 Action"을 3줄 이내로 요약 출력 (어떤 Input 지표를 먼저 / 무슨 검증으로 / 왜).
- 끝에 한 줄: "data/의 CSV를 본인 데이터로 바꾸고 다시 `/build-dashboard` 하면 같은 퀄로 재생성됩니다."

## 핵심 원칙
- reference = 품질 기준선. 결과가 그보다 단순/다른 톤이면 다시 만든다.
- 복붙이 아니라 "구조 재사용 + 데이터 교체". 숫자는 항상 실제 분석값.
- 위계를 거슬러 가장 상류의 망가진 Input 지표를 먼저 고치는 Action을 권고한다.
