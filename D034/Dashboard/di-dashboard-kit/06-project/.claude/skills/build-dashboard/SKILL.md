---
name: build-dashboard
description: data/의 매출·주문 CSV(또는 xls/xlsx)를 분석해, templates/reference.html과 동일한 퀄리티의 리테일/이커머스 대시보드를 output/에 생성하는 스킬. 매출, 이익, 마진율, 반품률 등 리테일 KPI 기반. "리테일 대시보드 만들어줘", "/build-retail-dashboard" 시 사용.
argument-hint: "[CSV/XLS 경로 — 생략 시 data/orders.csv]"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Bash(python3 *)
---

# build-retail-dashboard — 리테일/이커머스 대시보드 자동 생성

원본 `build-dashboard` 스킬(마케팅 캠페인 전용)을 리테일 판매 데이터용으로 재구성한 버전.
CLAUDE.md(리테일 버전)와 함께 쓴다 — KPI 정의·필드 매핑은 전부 그쪽에 있다.
**반드시 아래 5단계를 순서대로 수행한다. 단계를 건너뛰지 않는다.**

## STEP 1 — 데이터 읽기 (EDA)

- 인자로 받은 파일(없으면 `data/orders.csv`)을 Read/Bash로 로드. `.xls`는 `pd.read_excel(engine="xlrd")`, `.xlsx`는 기본 엔진.
- 시트가 여러 개면(주문/반품 등) 시트 목록을 사용자에게 먼저 보여준다.
- 컬럼·행 수·기간·Category 등 그룹 목록을 한 줄로 요약해 보여준다.
- 필수 컬럼 확인: `order_date, order_id, category, sales, profit, discount`.
  - 컬럼명이 다르면 가장 가까운 것에 매핑하고 알려준다.
  - 반품 데이터(별도 시트/파일)가 있으면 `order_id, returned`도 매핑, 없으면 반품률/퍼널 계산을 생략한다고 알린다.

## STEP 2 — KPI 계산 (실제 숫자)

- CLAUDE.md의 KPI 정의표대로 계산: 총매출/총이익/이익률/주문건수/객단가/반품률/평균할인율.
- **chData는 Category 하나의 그룹 기준으로만 만든다** (CLAUDE.md "그룹 팔레트" 섹션 참조 — Sub-Category로 따로 만들지 않는다). 각 원소에 `sales, profit, discountAvg, orders, ordersReturned` 필드를 채운다.
- 이익률 내림차순으로 정렬.
- 기간 시계열(카테고리 × 월/분기 매출·이익)을 집계.
- **할인율(discountAvg) vs 이익률의 선형회귀**를 이 단계에서 미리 계산해 `slope`, `intercept`를 구해둔다 — STEP4 시뮬레이터에 그대로 쓴다.
- Sub-Category 단위로 총이익 순위도 별도로 계산해둔다 — 차트엔 안 쓰지만 STEP5 텍스트 요약에 필요하다 (Category 합계엔 적자 Sub-Category가 묻힐 수 있음).
- 계산은 Bash(python)로 실제 수행하고, 결과 수치를 표로 한 번 보여준다. **추정·반올림 임의값 금지.**

## STEP 3 — 레퍼런스 구조 흡수

- `templates/reference.html`을 **반드시 Read** 한다. 없으면 즉시 중단하고 알린다.
- **CLAUDE.md에 적힌 색상 값·상수를 곧이곧대로 믿지 말고, reference.html의 실제 `const chColors=...`, 클러스터 `backgroundColor`/`borderColor` 리터럴을 직접 읽어서 확인한다.** (이번 프로젝트에서 CLAUDE.md 설명과 실제 코드가 어긋난 전례가 있었다 — chColors 그라데이션 설명, `--c1` HIGH클러스터 설명 둘 다 실제 코드와 달랐다.)
- HTML 골격, CSS 토큰, chart.js 초기화 패턴, `funnelSteps`/`chData`/시뮬레이터 코드의 정확한 필드 접근 표현식을 전부 확인한다.
- `⚠ SAMPLE` 주석 블록은 전량 교체 대상.
- 구조를 그대로 재사용한다 — 새로 디자인하지 않는다.

## STEP 4 — 데이터 주입해서 렌더

- 레퍼런스 구조 위에 STEP 2의 실제 계산값을 채워 `output/retail_dashboard.html` 생성.
- **CLAUDE.md의 "필드 접근 예외" 표를 그대로 따른다** — 이 표에 나온 지점(totals, kMeans 좌표식, donutChart 데이터, roiVals, DAILY_SAMPLE 키, funnelSteps, 시뮬레이터, 표 헤더/행)은 "값 교체"가 아니라 "필드명/계산식 자체"를 바꿔야 한다. 그 외 지점은 값만 교체한다.
- 시뮬레이터는 반드시 STEP2에서 구한 회귀식(`newMargin=intercept+slope*newDiscount`)으로 교체한다. 원본의 `ratio**0.7` 체감수확 공식을 그대로 두면 안 된다 — 방향이 반대인 관계에 마케팅 가정을 씌우는 것이라 실패로 간주한다.
- AI 클러스터 산점도는 Category 3개, X=할인율, Y=이익률로 그리고, 색은 reference.html에서 확인한 HIGH/LOW 리터럴 색을 그대로 쓴다(`chColors`나 `--c1`을 쓰지 않는다).
- 스파크라인·시계열은 반드시 실제 계산 배열로. `Math.random()` 금지.
- 카드 제목은 결론/질문형. KPI 수치는 검정(`--t1`) 고정.
- `delta` 뱃지에는 비교 기준 기간을 라벨로 명시한다.
- CLAUDE.md의 금지 항목을 위반하지 않았는지 자체 점검.
- 차트 내 데이터 레이블, 범례의 경우 다른 항목과 텍스트가 겹치지 않게 위치를 조정한다.
- 좌측 탭 "매출 추이", "주문 퍼널", "할인 시뮬레이터" 탭 클릭 시 관련된 위젯들에 음영 하이라이트를 1초간 하여 강조한다

## STEP 4-1 — 고급 분석: 크로스셀링 & 지역 분석 데이터 준비

- **크로스셀링 분석** (CLAUDE.md STEP 5 항목 9):
  - Category 조합 4가지를 `advancedData.crossSells` 배열로 정리
  - 각 조합의 판매횟수·총이익·평균이익 계산
  - 각 조합 내 Sub-Category 크로스셀링(같은 주문에서 함께 팔린 상품군 쌍) Top 5를 `advancedData.categorySubCategoryData` 객체로 정리
  - **중요**: Sub-Category 쌍 데이터는 평균이익 기준 내림차순 정렬 — 이 순서 자체가 인사이트
  - 표 컬럼: `상품군 조합 / 판매횟수 / 총이익 / 평균이익`

- **지역별 상품 매출 분석** (CLAUDE.md STEP 5 항목 10):
  - `advancedData.regionProducts` 객체: 4개 지역 × 15~20개 Sub-Category의 매출액 (드롭다운 필터용)
  - 드롭다운 옵션: "전체 지역"(스택형), "Central", "East", "South", "West"(그룹형 또는 스택형)
  - 지역별 색: Central `#C63B3F`, East `#31538F`, South `#1B7F49`, West `#8A6100` — CLAUDE.md 토큰이 아닌 독립적 데이터색

- HTML에 마크업 추가: 크로스셀링 테이블(행 클릭 시 상세 패널), 지역 드롭다운+막대 차트

## STEP 5 — 전달

- 저장 경로의 절대경로 file:// 링크를 안내한다.
- "이번 데이터 기준 카테고리/할인 정책 권고"를 3줄 이내로 요약 출력.
- **Sub-Category 레벨의 적자 항목(STEP2에서 미리 계산해둔 것)을 반드시 한 줄 따로 언급한다** — Category 합계만 보면 놓치는 인사이트이기 때문.
- 끝에 한 줄: "data/의 파일을 본인 데이터로 바꾸고 다시 `/build-retail-dashboard` 하면 같은 퀄로 재생성됩니다."

## 핵심 원칙
- reference = 품질 기준선. 결과가 그보다 단순/다른 톤이면 다시 만든다.
- 복붙이 아니라 "구조 재사용 + 데이터 교체". 숫자는 항상 실제 분석값.
- reference.html의 상수·색상은 코드를 직접 읽어서 확인한다 — CLAUDE.md의 설명은 참고용이지 절대 기준이 아니다.
- 마케팅 원본과 KPI 정의가 다르므로 두 스킬을 하나로 합치지 않는다.
