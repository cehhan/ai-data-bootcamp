---
name: build-dashboard
description: data/의 캠페인 CSV를 분석해, templates/reference.html과 동일한 퀄리티의 마케팅 대시보드를 output/에 생성하는 스킬. "대시보드 만들어줘", "/build-dashboard" 시 사용.
argument-hint: "[CSV 경로 — 생략 시 data/campaigns.csv]"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Bash
---

# build-dashboard — 마케팅 대시보드 자동 생성

수강생이 이 명령 하나만 치면, 강사 퀄리티의 대시보드가 자기 데이터로 나온다.
**반드시 아래 5단계를 순서대로 수행한다. 단계를 건너뛰지 않는다.**

## STEP 1 — 데이터 읽기 (EDA)
- 인자로 받은 CSV(없으면 `data/campaigns.csv`)를 Read/Bash로 로드.
- 컬럼·행 수·채널 목록·기간을 한 줄로 요약해 사용자에게 보여준다.
- 필수 컬럼 확인: `week, channel, impressions, clicks, conversions, spend, revenue`.
  - 컬럼명이 다르면 가장 가까운 것에 매핑하고, 매핑 결과를 알려준다.

## STEP 2 — KPI 계산 (실제 숫자)
- `CLAUDE.md`의 계산식대로 채널별 + 전체 ROAS / ROI / CTR / CVR / CPA / CPC를 계산한다.
- 채널을 **ROAS 내림차순**으로 정렬. 1위·꼴찌 채널을 식별.
- 주간 시계열(채널 × week ROAS)을 집계.
- 계산은 Bash(python)로 실제 수행하고, 결과 수치를 표로 한 번 보여준다. **추정·반올림 임의값 금지.**

## STEP 3 — 레퍼런스 구조 흡수
- `templates/reference.html`을 **반드시 Read** 한다.
- HTML 골격(사이드바, STEP 1~4, KPI 카드 6개, 차트 wrap, 시뮬레이터, 표), CSS 토큰, chart.js 초기화 패턴을 파악한다.
- `⚠ SAMPLE` 주석이 붙은 블록(`KPI_SPARK_SAMPLE`, `DAILY_SAMPLE`, `delta`)은 **전량 교체 대상**이다.
- 이 구조를 그대로 재사용한다 — 새로 디자인하지 않는다.

## STEP 4 — 데이터 주입해서 렌더
- 레퍼런스 구조 위에 STEP 2의 **실제 계산값**을 채워 `output/marketing_dashboard.html` 생성.
- 교체 대상: KPI 카드 6개 값 + `KPI_SPARK_SAMPLE`(7포인트 × 6) + `delta` 뱃지,
  `DAILY_SAMPLE`(채널별 일별 매출), `chData`, 퍼널 수치, 시뮬레이터 BASE 값, 요약 표.
- **`chData`를 ROAS 내림차순으로 정렬**하면 `chColors[i]`가 진→연으로 자동 매핑된다. 색을 개별 지정하지 않는다.
- 스파크라인·시계열은 반드시 **실제 계산 배열**로 채운다. `Math.random()` 등 생성 함수를 만들지 않는다.
- 카드 제목은 결론/질문형으로. KPI 수치는 검정(`--t1`) 고정.
- `CLAUDE.md`의 금지 항목(한쪽 border, 수치 색, 장식)을 위반하지 않았는지 자체 점검.

## STEP 5 — 전달
- 저장 경로의 **절대경로 file:// 링크**를 안내한다.
- "이번 데이터 기준 예산 배분 권고"를 3줄 이내로 요약 출력 (어디 늘리고 / 어디 줄이고 / 왜).
- 끝에 한 줄: "data/의 CSV를 본인 데이터로 바꾸고 다시 `/build-dashboard` 하면 같은 퀄로 재생성됩니다."

## 핵심 원칙
- reference = 품질 기준선. 결과가 그보다 단순/다른 톤이면 다시 만든다.
- 복붙이 아니라 "구조 재사용 + 데이터 교체". 숫자는 항상 실제 분석값.
