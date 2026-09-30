---
name: build-dashboard
description: data/의 구독 CSV를 분석해, templates/reference.html과 동일한 퀄리티의 코호트 리텐션·MRR·LTV 대시보드를 output/에 생성하는 스킬. "대시보드 만들어줘", "/build-dashboard" 시 사용.
argument-hint: "[CSV 경로 — 생략 시 data/subscriptions.csv]"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Bash
---

# build-dashboard — 리텐션 대시보드 자동 생성

수강생이 이 명령 하나만 치면, 강사 퀄리티의 리텐션 대시보드가 자기 데이터로 나온다.
**반드시 아래 5단계를 순서대로 수행한다. 단계를 건너뛰지 않는다.**

## STEP 1 — 데이터 읽기 (EDA)
- 인자로 받은 CSV(없으면 `data/subscriptions.csv`)를 Read/Bash로 로드.
- 컬럼·행 수·코호트(가입월) 목록·관측 기간을 한 줄로 요약해 사용자에게 보여준다.
- 필수 컬럼 확인: `user_id, signup_month, active_month, mrr, churned` (+ 선택 `plan`).
  - 컬럼명이 다르면 가장 가까운 것에 매핑하고, 매핑 결과를 알려준다.

## STEP 1.5 — 기준월 판정 (반드시 수행)
- 월별 `churned=1` 건수를 센다. **마지막 달이 0건이면 집계 미완료 달**이므로 기준월에서 제외한다.
- 확정한 `기준월`을 사용자에게 한 줄로 알린다 (예: `기준월 = 2024.05 (2024.06은 churn 0건으로 제외)`).
- 이후 MRR·Revenue Churn·신규 MRR·NRR은 **모두 이 기준월**로 계산한다. 코호트·LTV는 전체 기간을 쓴다.

## STEP 2 — 코호트·MRR·LTV 계산 (실제 숫자)
- **코호트 매트릭스**: 가입월별로 그룹핑 → 각 경과월 M{n}(active_month − signup_month)에 살아있는 unique user 수 / M0 user 수 × 100. 가입월 오름차순 행, M0..M5 열. M0=100. 미관측 셀은 `null`.
- **MRR 구성**: 월별 신규(signup==active) / Expansion(전월 대비 동일유저 mrr 증가) / Churned(그 달 churned=1 직전 mrr, 음수) MRR을 집계. 성장률 = (당월 총MRR − 전월) / 전월 × 100.
- **Revenue Churn / NRR**: `CLAUDE.md`의 계산식대로. `BASE_MRR`=마지막 월 총 MRR, `BASE_NRR`=마지막 월 NRR로 What-if 기준값 고정.
- **LTV 분포**: 유저별 생애 mrr 합을 구간(`~₩200K…₩5M+`)으로 버킷팅 → 구간별 고객 비중(%).
- **플랜 세그먼트**: 플랜별 고객수·MRR·Churn·NRR·LTV·MoM. churn 낮은 순 정렬.
- 계산은 Bash(python)로 실제 수행하고, 코호트 매트릭스와 KPI를 표로 한 번 보여준다. **추정·임의값 금지.**

## STEP 3 — 레퍼런스 구조 흡수
- `templates/reference.html`을 **반드시 Read** 한다.
- HTML 골격(사이드바, KPI 6카드, MRR 스택, What-if 슬라이더, 코호트 히트맵, Pareto, LTV, AI카드, 세그먼트표), CSS 토큰, chart.js 초기화 패턴을 파악한다.
- `grep -n "const .*=" templates/reference.html` 으로 교체 대상 데이터 배열 위치를 모두 확인한다:
  `sparkData / months,newMRR,expMRR,churnMRR,growthRate / cohortMonths,cohortSizes,cohortData / paretoCount,paretoRevenue / ltvLabels,ltvData / aiItems / segments`
- 이 구조를 그대로 재사용한다 — 새로 디자인하지 않는다.

## STEP 4 — 데이터 주입해서 렌더
- 레퍼런스 구조 위에 STEP 2의 **실제 계산값**으로 const 배열만 정규식 교체해 `output/retention_dashboard.html` 생성.
- **배열 필드명·길이·형식은 100% 동일 유지** (예: `cohortData`는 6×6, M0=100, null 유지). JS 로직 불변.
- KPI 카드 6개 숫자, 코호트 색(chColor 규칙), 세그먼트 색(--c1~--c5), 제목/기준일을 새 값으로.
- 카드 제목은 결론/질문형. KPI 수치는 검정 고정.
- `CLAUDE.md`의 금지 항목(한쪽 border, 수치 색, 필드명 변경)을 위반하지 않았는지 자체 점검.

## STEP 5 — 전달 + 리텐션 개선 권고
- 저장 경로의 **절대경로 file:// 링크**를 안내한다.
- "이번 데이터 기준 리텐션 개선 권고"를 3줄 이내로 요약 출력 (어느 코호트/플랜이 새는지 / 무엇을 할지 / 왜 — What-if 영향 수치 포함).
- 끝에 한 줄: "data/의 CSV를 본인 구독 데이터로 바꾸고 다시 `/build-dashboard` 하면 같은 퀄로 재생성됩니다."

## 핵심 원칙
- reference = 품질 기준선. 결과가 그보다 단순/다른 톤이면 다시 만든다.
- 복붙이 아니라 "구조 재사용 + 데이터 교체". 숫자는 항상 실제 분석값.
- const 배열 **필드명/형식 불변**이 차트 안 깨지는 절대 조건이다.
