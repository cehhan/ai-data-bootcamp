# CLAUDE.md — Superstore 성과 대시보드 (리테일 버전, reference.html 검증 완료)

## 이 프로젝트의 목표
`data/`의 Superstore 주문(Orders) 데이터(CSV/XLS)를 받아, **이 폴더의 디자인을 그대로 따르는** 카테고리별 성과 대시보드 HTML을 `output/`에 만든다.
"예쁜 화면"이 아니라 "3초 안에 어디서 마진이 새고 있는지, 어떤 카테고리/할인 정책을 조정해야 이익이 오르는지 아이디어를 낼 수 있는 화면"을 만든다.

> 이 문서는 `templates/reference.html`의 실제 JS 코드를 직접 읽어 검증한 버전이다.
> 아래 값들은 전부 reference.html 원문과 대조 확인했다 (색상 배열, 클러스터 색, chData 연동 구조, 시뮬레이터 수식 포함).

---

## 가장 중요한 규칙 (반드시 먼저 읽을 것)
**처음부터 새로 디자인하지 않는다.** 항상 `templates/reference.html`을 먼저 Read 하고,
그 **구조·레이아웃·색상·차트 종류·카드 패턴을 그대로 재사용**한 뒤, **숫자와 인사이트만 새 데이터로 교체**한다.

- 레퍼런스는 **"품질 기준선"** 이다. 결과물이 레퍼런스보다 단순하거나 다른 톤이면 실패다.
- 레퍼런스에 박힌 수치는 **전부 디자인용 예시**다. `⚠ SAMPLE` 마커가 붙은 블록은 **전량 교체 대상**이다.
- 단, **복붙이 아니다.** 데이터는 반드시 새로 분석해서 실제 계산값을 넣는다.
- **JS 로직·차트 초기화·플러그인은 원칙적으로 바꾸지 않는다.** 단, "필드 접근 예외" 섹션에 명시된 지점은 리테일 데이터에 맞는 필드명/수식으로 반드시 바꿔야 한다 (아래 참조 — 이건 예외가 아니라 필수다).
- 데이터로 계산할 수 없는 지표는 **만들어내지 않는다.** 컬럼이 없으면 진행을 멈추고 사용자에게 알린다.

## 디자인 토큰 (reference.html `:root`에서 직접 추출 — 변경 없음)
```css
--bg:#F5F6F8; --card:#FFFFFF; --border:#E6E2E2; --sidebar:#2B2B30;
--t1:#2B2B30;        /* KPI 수치 — 검정 고정, 빨강/초록 금지 */
--t2:#4A4A52; --t3:#6A6A73; --t4:#8A8A94;
--c1:#7E2124;        /* 순수 UI 장식용 (STEP 번호 배지, 아이콘 배경 등). 데이터/클러스터 색이 절대 아니다 */
--c2:#A83035; --c3:#C63B3F; --c4:#D9565A; --c5:#E66F72;
--green:#1B7F49; --red:#C0392B;
--green-bg:#E8F5EE; --red-bg:#FBEAE8;
--coral:#F7585C; --navy:#31538F; --navy-l:#6E8CC4;
--amber:#8A6100; --amber-bg:#F6F0E2; --navy-bg:#EDF1F8;
--font:'Pretendard',-apple-system,sans-serif; --r:12px; --grid:#ECECF0;
```
- 폰트: Pretendard, CDN `cdn.jsdelivr.net/gh/orioncactus/pretendard` — 확인 완료.
- 차트: `chart.js@4.4.0` (jsdelivr CDN) — 확인 완료. 버전 바꾸지 않는다.

### 그룹 팔레트 = JS `chColors` 배열 (reference.html 원문 그대로, 절대 바꾸지 않음)
```js
const chColors=["#C63B3F","#31538F","#1B7F49","#8A6100","#8A8A94"];
// 코랄 · 네이비 · 초록 · 앰버 · 회색 — "진→연 그라데이션"이 아니라 역할 기반 고정색이다.
```
- **`chData`를 그룹 순서 기준(아래 "정렬 기준" 참조)으로 정렬한 뒤 `chColors[i]`를 index로 매핑**한다. 배열 길이가 5보다 짧아도(3~4개) 문제없다 — 남는 색은 그냥 안 쓰인다.
- **`chData`는 도넛·효율 막대·산점도(클러스터)·요약 표·시뮬레이터 탭까지 전부 이 배열 하나를 공유한다.** 즉 "이 차트는 Category, 저 차트는 Sub-Category"처럼 그룹 단위를 나눠 쓸 수 없다 — 반드시 **하나의 그룹 기준**으로 통일해야 한다.
- **그룹 기준은 Category(3개)로 통일한다** (Furniture/Office Supplies/Technology). Region(4개)도 대안 가능하지만, Category가 EDA에서 이미 다룬 스토리와 연결되어 더 낫다.
  - **주의**: Category 레벨로 합치면 "Tables·Bookcases 적자" 같은 Sub-Category 단위 인사이트가 카테고리 합계 안에 묻힌다(Furniture 카테고리 자체는 순이익 흑자). 이 디테일은 차트가 아니라 **STEP 5 텍스트 요약에서 별도로 짚어준다.**
  - Sub-Category(17개)를 그대로 쓰면 `chColors`가 5개뿐이라 색이 깨진다. 굳이 쓰려면 CLAUDE.md의 "범주형 최대 5색, 그 이상은 회색+직접 라벨" 규칙대로 상위 5개만 색을 입히고 나머지는 회색 처리해야 하는데, 이 경우 구현 난이도가 크게 올라간다 — 권장하지 않는다.

## 색 사용 규칙 (변경 없음)
색은 **네 가지 일 중 하나**를 할 때만 쓴다 — 분류 · 크기 · 강조 · 의미. 넷 다 아니면 장식이다.

| 역할 | 색 | 쓰는 곳 |
|---|---|---|
| 문제 · 하락 · 나쁜 예 | 코랄 `--c3 #C63B3F` | 적자 카테고리·반품 위험·경고 지표 |
| 해법 · 좋은 예 · 결론 | 네이비 `--navy #31538F` | 목표선·기준선 |
| 정상 · 상승 | `--green #1B7F49` | 이익 증가 뱃지, 양호 상태, **AI 클러스터 HIGH 그룹** |
| 나쁨 · 하락 | `--red #C0392B` | **AI 클러스터 LOW 그룹**, 하락 뱃지 |
| 주의 | `--amber #8A6100` | 중간 위험 |
| 중립 · 비활성 | `--t4 #8A8A94` | 나머지 |
| 순수 UI 장식 | `--c1 #7E2124` | STEP 번호 배지 등 — **데이터색 아님** |

- 범주형은 코랄→네이비→초록→앰버→회색 순 최대 5색. 그 이상은 회색 + 직접 라벨.
- 강조 그룹은 한 차트에 하나. 같은 변수는 차트가 바뀌어도 같은 색 유지.
- 색만으로 정보를 나르지 않는다 — 라벨·아이콘·값 표기 병행(색각 이상 8%).

## chData 스키마 (리테일용, Category 기준)
```js
const chData=[
  {ch:"Office Supplies", sales:.., profit:.., discountAvg:.., orders:.., ordersReturned:..},
  {ch:"Furniture",       sales:.., profit:.., discountAvg:.., orders:.., ordersReturned:..},
  {ch:"Technology",      sales:.., profit:.., discountAvg:.., orders:.., ordersReturned:..},
];
```
- `sales`=sum(Sales), `profit`=sum(Profit), `discountAvg`=mean(Discount), `orders`=nunique(Order ID), `ordersReturned`=해당 카테고리 반품 주문 수(Returns 시트 조인, 없으면 0으로 두고 반품률 카드에 "데이터 없음" 표시)
- **정렬 기준: 이익률(`profit/sales`) 내림차순.** 원본의 ROAS 정렬 자리를 대체.

## 핵심 KPI 정의 (계산식 고정)
| 지표 | 계산식 | 표기 |
|---|---|---|
| 총매출 | sum(Sales) | `$` |
| 총이익 | sum(Profit) | `$` |
| 이익률 | sum(Profit) / sum(Sales) × 100 | `%` |
| 주문건수 | nunique(Order ID) | 정수 |
| 객단가(AOV) | 총매출 / 주문건수 | `$` |
| 반품률 | 반품 주문 수 / 주문건수 × 100 | `%` |
| (표·클러스터 보조지표) 평균 할인율 | mean(Discount) × 100 | `%` |
- 비율은 `%`, 증감은 `%p`로 구분 표기.
- 원본의 ROAS/ROI 이중 지표는 **이익률 하나로 통합** — 리테일엔 별도 "투입비용" 축이 없어서.

## 대시보드 구성 (reference의 STEP·카드 번호 순서 유지)

**STEP 1 — 핵심 지표 한눈에 보기**
1. **KPI 카드 6개**: `총매출 · 총이익 · 이익률 · 주문건수 · 객단가 · 반품률`
   - 각 카드에 7포인트 스파크라인 + 전기 대비 `delta` 뱃지(비교 기준 기간을 라벨로 명시, 예: "전분기 대비"). 난수 생성 금지.
   - **이상 감지 뱃지는 반품률 카드에 배정** — 카테고리별 반품률에 z-score 적용, 임계치(|z|>1.3) 초과 카테고리가 있으면 표시. 원본의 CVR 이상탐지 자리를 대체.

**STEP 2 — 매출 흐름과 카테고리 구조**
2. **매출 추이 분석** (`trendChart`, line) — 카테고리별 기간 매출 + 다항회귀 예측선(데이터 기간에 맞춰 주/월/분기 자동 선택).
3. **매출 비중** (`donutChart`, donut) — `chData.map(d=>d.sales)` 기준 (원본은 `d.spend` — 필드명 교체).

**STEP 3 — 카테고리 효율·클러스터·주문 퍼널**
4. **카테고리 효율 비교** (`roiChart`, 가로 막대) — 값은 이익률(`d.profit/d.sales*100`, 원본은 `(d.rev-d.spend)/d.spend*100`) — 정렬은 이미 이익률 기준이라 원본처럼 "정렬 기준과 그리는 기준이 다르다"는 예외가 없어짐(원본은 ROAS 정렬 + ROI로 그리는 이중 기준이었음, 리테일은 단일 기준으로 단순화).
5. **AI 클러스터 분석** (`scatterChart`, scatter) — X=평균 할인율, Y=이익률, **Category 3개 단위**(Sub-Category 아님 — 위 "그룹 팔레트" 참조), k-means(k=2). 색은 원본 그대로 **HIGH=`rgba(53,201,149,.8)`/`#1B7F49`(초록), LOW=`rgba(239,125,134,.8)`/`#C0392B`(빨강)** — `chColors`나 `--c1`이 아니다.
   - **표본 가드 문구 필수**: 그룹이 3개뿐이라 클러스터링의 통계적 의미가 제한적임을 명시한다.
6. **주문 퍼널** — 2단계: `전체 주문(totalOrders) → 정상 완료 주문(totalOrders - totalReturned)`. 원본은 노출→클릭→전환 3단계였지만, funnel 배열은 길이 제약이 없으므로(reference.html 코드 확인 완료) 2단계로 줄여도 구조가 깨지지 않는다. 반품 데이터가 전혀 없으면 이 카드 대신 "카테고리별 평균 할인율 비중" 막대로 대체.

**STEP 4 — 시뮬레이션과 액션**
7. **할인율 시뮬레이션** (슬라이더 + 카테고리 탭) — **원본의 `newRev = rev * ratio^0.7` 체감수확 모델은 그대로 못 쓴다.** 이건 "광고비를 늘리면 매출이 체감 수확으로 증가한다"는 마케팅 특유 가정이라, 방향 자체가 반대인 할인-마진 관계엔 안 맞는다.
   - **교체 로직**: STEP 2에서 할인율(discountAvg) vs 이익률 관계를 선형회귀로 근사해 `slope`, `intercept` 상수를 구한다. `newMargin = intercept + slope*newDiscount`, `newProfit = sales*newMargin` (sales는 할인율 변화에 영향받지 않는다고 가정 — 이 가정을 화면에 짧게 명시한다). 슬라이더 범위는 -10%p~+10%p 정도로 좁힌다(원본 -50~+50%는 광고비 조정 폭이라 할인율엔 과함).
   - 탭은 카테고리 3개, 나머지 UI/슬라이더 이벤트 리스너 구조는 원본 그대로.
8. **카테고리 성과 요약 · 액션 아이템** (표) — 컬럼: `카테고리 / 매출 / 이익 / 이익률 / 객단가 / 반품률 / 평균 할인율` + HIGH·LOW 뱃지(항목 5의 클러스터 결과 재사용).

**STEP 5 — 고급 분석: 크로스셀링 & 지역별 성과**
9. **카테고리 크로스셀링 조합 분석** (계층적 분석)
   - **기본 레이어**: Category 조합 기준 (4가지: "Office Supplies + Technology", "Furniture + Office Supplies + Technology", "Furniture + Office Supplies", "Furniture + Technology")
   - **테이블 컬럼**: `카테고리 조합 / 판매횟수 / 총이익 / 평균이익`
   - **상세 레이어** (행 클릭 시): Sub-Category 크로스셀링 분석 (같은 주문에서 함께 팔린 상품군 쌍)
     - 각 조합 내 Top 5 Sub-Category 쌍을 평균이익 기준 내림차순 정렬
     - 예: "Chairs + Machines" ($377.25 평균), "Appliances + Paper" ($147.74 평균)
   - 이익이 음수인 조합은 빨강(`--red #C0392B`), 양수는 초록(`--green #1B7F49`)으로 표시.
   - **주의**: 개별 Sub-Category 쌍은 통계적 표본 크기가 작을 수 있음(1~20회) — 인사이트는 방향성(어떤 쌍이 선호되는가)에만 사용하고 단정적 결론 금지.

10. **지역별 상품 매출 분석** (드롭다운 + 막대 차트)
    - 드롭다운 필터: "전체 지역" (기본) / "Central" / "East" / "South" / "West"
    - **"전체 지역" 선택 시**: 스택형 막대 (각 지역을 고유 색으로 구분)
    - **단일 지역 선택 시**: 그룹형 막대 (Sub-Category 간 비교)
    - Y축: Sub-Category (약 17~21개), X축: 매출액
    - 지역별 색: Central `#C63B3F`, East `#31538F`, South `#1B7F49`, West `#8A6100` (CLAUDE.md 토큰과 무관한 데이터색)
    - 지역과 상품이 많으면 Y축이 좁아질 수 있음 — 위젯 높이 조정 및 스크롤 지원.

> 이 10개(STEP 1~5, 항목 1~8 + 고급분석 9~10)가 최종 구성이다. 항목 6(퍼널) 또는 항목 10(지역)은 데이터 부재 시 대체 또는 생략 가능.

---

## 필드 접근 예외 — "값만 교체"가 아니라 표현식 자체를 바꿔야 하는 지점
아래는 reference.html에 `.spend`, `.imp`, `.clk`, `.cv`, `.rev` 필드가 하드코딩된 위치다. 리테일 chData엔 이 필드들이 없으므로, **값이 아니라 참조하는 필드명/계산식 자체를 바꿔야 한다.** (JS 로직을 안 건드린다는 원칙의 유일한 예외.)

| 원본 위치 | 원본 표현식 | 리테일 교체 |
|---|---|---|
| totals | `totalSpend/totalRev/totalClk/totalImp/totalCv` (5개 reduce) | `totalSales/totalProfit/totalOrders/totalReturned` (4개로 축소) |
| 파생지표 | `roi/ctr/cvr/cpa` 계산식 | `margin = totalProfit/totalSales*100`, `aov = totalSales/totalOrders`, `returnRate = totalReturned/totalOrders*100` |
| 이상탐지 | `cvrArr` (z-score on cv/clk) | 카테고리별 반품률 배열에 z-score 적용 |
| kMeans 좌표 | `x:d.clk/d.imp*100, y:d.cv/d.clk*100` | `x:d.discountAvg*100, y:d.profit/d.sales*100` — **kMeans 함수의 반복/재분류 로직 자체는 그대로 둔다.** |
| donutChart 데이터 | `chData.map(d=>d.spend)` | `chData.map(d=>d.sales)` |
| roiVals | `(d.rev-d.spend)/d.spend*100` | `d.profit/d.sales*100` |
| DAILY_SAMPLE 키 | 한글 채널명(`이메일`,`검색`...) | Category 영문/한글명(`Furniture`,`Office Supplies`,`Technology`) |
| funnelSteps | `totalImp/totalClk/totalCv` (3단계) | `totalOrders/totalNonReturned` (2단계) |
| 시뮬레이터 | `newRev=rev*ratio**0.7` | 위 STEP4-7 회귀식으로 전체 교체 (유일하게 "로직" 자체가 바뀌는 지점) |
| 표 헤더/행 | 채널·광고비·매출·ROI·CTR·CVR·CPA·CPC, `d.clk/d.imp` 등 | 카테고리·매출·이익·이익률·객단가·반품률·평균할인율 |

## 금지 (변경 없음)
- reference를 무시하고 새 레이아웃을 만드는 것
- 레퍼런스 숫자를 그대로 남겨두는 것 / `Math.random()`으로 차트 데이터 생성
- const 배열의 필드명·길이·형식을 바꾸는 것(위 "필드 접근 예외" 표에 명시된 곳 제외) / 그 외 JS 로직 수정
- KPI 수치에 색 입히기 / 한쪽 변만 있는 border
- 차트 종류를 이유 없이 늘리기 / 장식용 그라디언트 / 토큰 밖의 색을 새로 만드는 것
- `%`와 `%p` 혼용 / 표본이 작은 구간을 단정적으로 해석(표본 가드 문구 필수 — 특히 클러스터 3개, 캐나다 200건)
- 글자 11px 미만 / 대비 3:1 미만 색을 데이터 마크·텍스트에 사용
- 좁은 막대 안쪽에 값을 넣어 잘리게 두는 것

## 작업이 끝나면
- `output/retail_dashboard.html`로 저장, 절대경로 file:// 링크 안내
- "카테고리/할인 정책 권고 1줄 요약" + **Sub-Category 적자(Tables/Bookcases) 별도 언급** 텍스트 출력
