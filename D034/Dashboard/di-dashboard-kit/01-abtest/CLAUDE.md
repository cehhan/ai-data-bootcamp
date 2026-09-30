# CLAUDE.md — A/B 테스트 실험 결과 대시보드

## 이 프로젝트의 목표
`data/`의 실험 CSV를 받아, **이 폴더의 디자인을 그대로 따르는** A/B 테스트 의사결정 대시보드 HTML을 `output/`에 만든다.
"예쁜 화면"이 아니라 "3초 안에 어떤 변형(Variant)을 배포할지 보이는 화면"을 만든다.

---

## 가장 중요한 규칙 (반드시 먼저 읽을 것)
**처음부터 새로 디자인하지 않는다.** 항상 `templates/reference.html`을 먼저 Read 하고,
그 **구조·레이아웃·색상·차트 종류·카드 패턴을 그대로 재사용**한 뒤, **숫자와 인사이트만 새 데이터로 교체**한다.

- 레퍼런스는 **"품질 기준선"** 이다. 결과물이 레퍼런스보다 단순하거나 다른 톤이면 실패다.
- 레퍼런스에 박힌 수치는 **전부 디자인용 예시**다. `⚠ SAMPLE` 마커가 붙은 블록은 **전량 교체 대상**이다.
  산출물에 레퍼런스 숫자가 하나라도 남아 있으면 실패다.
- 단, **복붙이 아니다.** 데이터는 반드시 새로 분석해서 실제 계산값을 넣는다 (아래 지표 정의대로).
- **JS 로직·차트 초기화·플러그인·배열 필드명/형식은 절대 바꾸지 않는다.** const 데이터의 **값만** 교체한다.
  (필드명·배열 길이가 바뀌면 차트가 깨진다.)
- 데이터로 계산할 수 없는 지표는 **만들어내지 않는다.** 컬럼이 없으면 진행을 멈추고 사용자에게 알린다.

## 디자인 토큰 (reference.html의 :root에서 추출 — 동일하게 고정)
```css
--bg:#F5F6F8;        /* 컨텐츠 배경 */
--card:#FFFFFF;      /* 카드 배경 */
--border:#E6E2E2;    /* 카드 테두리 */
--sidebar:#2B2B30;   /* 사이드바 (네이비) */
--t1:#2B2B30;        /* KPI 수치 — 검정 고정, 빨강/초록 금지 */
--t2:#4A4A52; --t3:#64748B; --t4:#94A3B8;  /* 보조 텍스트 단계 */
--grid:#ECECF0;      /* 차트 그리드 */
--green:#1B7F49;     /* 좋음/상승/Ship */
--red:#C0392B;       /* 나쁨/하락/Stop·위험 */
--amber:#8A6100;     /* 경고(레퍼런스에선 네이비로 처리) */
--green-bg:#E8F5EE; --red-bg:#FBEAE8; --amber-bg:#F6F0E2; --navy-bg:#EDF1F8;
/* 효과크기 팔레트 (진→연, uplift 순) */
--c1:#7E2124; --c2:#5B6AB0; --c3:#7B8FCC; --c4:#A8B8E0; --c5:#D4DCF0;
--r:10px;
--t3:#6A6A73;
--t4:#8A8A94;
--c2:#A83035;
--c3:#C63B3F;
--c4:#D9565A;
--c5:#E66F72;
--coral:#F7585C;
--navy:#31538F;
--navy-l:#6E8CC4;
--red-bg:#FBEAE8;
--amber-bg:#F6F0E2;
--navy-bg:#EDF1F8;
--font:'Pretendard',-apple-system,sans-serif;
```
- 폰트: **Pretendard** (reference와 동일, CDN)
- 차트: reference가 쓰는 방식 그대로 — `chart.js`(CDN) + `<canvas>` / Forest Plot은 인라인 `<svg>`, 아이콘은 인라인 `<svg>`
- KPI 수치 색은 **검정(`--t1`) 고정**. 빨강/초록은 증감 화살표·뱃지·Decision 색에만.
- 임의 색 사용 금지. 위 토큰 밖의 색을 새로 만들지 않는다.

---

## 색 사용 규칙 (PART 1 Ch 6 · 모두의연구소 브랜드)
색은 **네 가지 일 중 하나**를 할 때만 쓴다 — 분류 · 크기 · 강조 · 의미. 넷 다 아니면 장식이다.

| 역할 | 색 | 쓰는 곳 |
|---|---|---|
| 문제 · 하락 · 나쁜 예 | 코랄 `--c3 #C63B3F` | 이탈·위험·경고 지표, 강조 |
| 해법 · 좋은 예 · 결론 | 네이비 `--navy #31538F` | 목표선·기준선, 2번째 범주 |
| 정상 · 상승 | `--green #1B7F49` | 증가 뱃지, 양호 상태 |
| 주의 | `--amber #8A6100` | 중간 위험 |
| 중립 · 비활성 | `--t4 #8A8A94` | 나머지, 강조 대비용 |
| 잉크 | `--t1 #2B2B30` | 수치·사이드바 |

- **범주형**은 코랄 → 네이비 → 정상(녹) → 앰버 → 회색 순으로 **최대 5색**. 그 이상은 회색 + 직접 라벨.
- **연속형**(코호트 리텐션 등 순서 있는 값)만 **단일 색상 램프**를 쓴다.
  값이 클수록 좋은 지표는 **네이비 램프**(진할수록 좋음), 나쁠수록 큰 지표는 **코랄 램프**.
- **강조 채널은 한 차트에 하나.** 색으로 강조했으면 크기는 건드리지 않는다.
- 같은 변수는 차트가 바뀌어도 **같은 색**을 유지한다.
- 상태색(정상/주의/위험)은 **상태에만** 쓴다. 범주 구분에 전용하지 않는다.
- 색만으로 정보를 나르지 않는다 — 라벨·아이콘·값 표기를 함께 둔다(색각 이상 8%).
- `--coral #F7585C`는 대비 3.2:1이라 **큰 면·배경 전용**이다. 작은 글자·선에는 `--c3`를 쓴다.

## 핵심 KPI 정의 (계산식 고정)
| 지표 | 계산식 | 표기 |
|---|---|---|
| 전환율(CVR) | conversions / users × 100 | `%` |
| 절대 차이(Absolute Δ) | CVR(B) − CVR(A) | `%p` |
| 상대 Uplift | (CVR(B) − CVR(A)) / CVR(A) × 100 | `%` |
| 표준오차(SE) | √( p_a(1−p_a)/n_a + p_b(1−p_b)/n_b ) | 비율 |
| z-통계량 | (p_b − p_a) / SE | 수치 |
| p-value | 양측검정, 2·(1 − Φ(\|z\|)) | `<0.001` / `0.0xx` |
| 95% 신뢰구간(CI) | Δ ± 1.96·SE (상대 uplift 환산) | `[+x%, +y%]` |
| 유의성(sig) | p < 0.05 → true | bool |
| 증분 매출 | revenue(B) − revenue(A) | `₩` (추정) |

### 표기 규칙 (절대/상대 혼용 금지)
- **비율 그 자체**는 `%` (예: CVR 6.8%).
- **두 비율의 차이**는 `%p` (예: +1.6%p). `%`와 `%p`를 절대 섞지 않는다.
- **상대 uplift**(`+30.8%`)와 **절대 delta**(`+1.6%p`)는 항상 따로 표기한다. 한 칸에 섞지 않는다.
- 증분 매출에는 "추정" 맥락을 유지한다(관측 revenue 차이 기반).

### 의사결정 규칙 (decision 필드)
| decision | 조건 | 색(decisionColors) |
|---|---|---|
| `ship` | sig=true AND uplift 상위 + guardrail 통과 | `#10B981` |
| `hold` | sig=true 이지만 효과 약함(작은 uplift) | `#4A7AB5` |
| `retest` | guardrail=SRM 등 실험 오염 | `#4A5F80` |
| `monitor` | sig=false 또는 guardrail 악화(AOV↓) | `#6B7280` |
| `stop` | sig=false AND uplift 미미 | `#EF4444` |
- Forest Plot·테이블·인사이트의 decision 값은 위 규칙으로 **일관되게** 산출한다.

---

## 대시보드 구성 (reference의 섹션 순서 유지 — 바꾸지 않는다)
1. **상단 KPI 6개 (row1)**: Active Experiments · Decision-Ready · Guardrail Pass Rate · Risk Alerts · 검증 완료율 · Incremental Revenue
   - 라벨은 reference 그대로. 값만 CSV 계산값으로 교체.
2. **누적 전환율 차이 + 95% CI (row2 좌, `cumulChart`)** — 라인 + CI 밴드. 대표 실험 2개의 일별 누적 Δ.
3. **실험 품질 경고 패널 (row2 우)** — SRM · Guardrail 악화 · 표본 부족 · 다중비교 보정.
4. **Forest Plot (row3 좌, `forestPlot` SVG)** — 실험별 효과크기(uplift)와 95% CI, 귀무가설(0) 세로선. `forestData`.
5. **세그먼트 스캐터 (row3 우, `segChart` bubble)** — X=상대 Uplift, Y=통계적 신뢰도, 원크기=표본. `segData`.
6. **AI 판정 인사이트 (row4 좌, `aiList`)** — 상위 실험 근거·제약·리스크·액션. `aiItems`.
7. **실험 의사결정 테이블 (row4 우, `decTable`)** — Control/Variant/Absolute Δ/Relative Uplift/CI/p/N/기간/Guardrail/Decision. `tableData`.

---

## 교체 대상 데이터 배열 (이것만 바꾼다)
| 배열 | 위치(레퍼런스 기준) | 필드 | 무엇을 채우나 |
|---|---|---|---|
| `tableData` | 의사결정 테이블 **+ 누적차이 라인** | exp,metric,ctrl,variant,abs,rel,ci,pval,n,runtime,guardrail,decision | 전체 실험 요약 한 행씩 |
| `forestData` | Forest Plot | name,effect,ci[lo,hi],n,sig,decision | 실험별 상대 uplift(%)+95%CI+표본+유의성+판정 |
| `segData` | 세그먼트 스캐터 | x,y,r,label,status | 세그먼트별 uplift(x)·신뢰도(y)·표본(r)·status |
| `aiItems` | AI 인사이트 | idx,name,decision,metric{...},constraint,risk,action | 상위 3개 실험 상세 |

- **누적 전환율 차이 차트는 별도 배열이 없다.** `CUMEXPS`가 `tableData`의 `abs`·`ci`·`rel`·`runtime`에서
  자동 파생되고, `genCum()`이 시드 기반 결정적 곡선을 그린다.
  → **`tableData`만 정확히 채우면 이 차트도 함께 갱신된다.** `CUMEXPS`·`genCum`·`srnd`는 건드리지 않는다.
- `decisionColors`,`statusColors`,`ciPlugin`,차트 옵션 등 JS 로직은 **건드리지 않는다.**
- **품질 경고 패널(`.warn-list`)은 하드코딩된 HTML이다.** SRM·Guardrail 악화·표본 부족·다중비교 항목을
  데이터에서 실제로 판정해 문구와 수치를 교체한다. 해당 사항이 없으면 그 항목을 삭제한다.
  - SRM 판정: variant별 `users`로 χ² 검정(df=1). **p < 0.01일 때만** SRM으로 표기한다.
  - Guardrail 악화: `revenue/conversions`로 AOV를 구해 A 대비 B의 감소폭을 쓴다.
  - 다중비교: Benjamini-Hochberg 적용. **분모는 전체 실험 수**다(세그먼트 행 수가 아니다).

---

## 금지
- reference를 무시하고 처음부터 새 레이아웃을 만드는 것
- 데이터 분석 없이 **레퍼런스 숫자를 그대로 남겨두는 것**
- **`Math.random()` 등으로 차트 데이터를 생성하는 것** (스파크라인·시계열 포함)
- const 배열의 **필드명·길이·형식을 바꾸는 것** / JS 로직 수정 (차트 깨짐)
- KPI 수치에 색 입히기 / 한쪽 변만 있는 border(border-left 등 단독)
- 차트 종류를 이유 없이 늘리기 / 장식용 그라디언트
- `:root` 토큰 밖의 색을 새로 만드는 것
- `%`와 `%p` 혼용 / 절대값과 상대값을 한 칸에 섞기
- 표본이 작은 구간을 단정적으로 해석하는 것 (표본 가드 문구를 붙인다)
- 글자를 11px 미만으로 줄이는 것 / 대비 3:1 미만인 색을 데이터 마크·텍스트에 쓰는 것
- 좁은 막대 **안쪽**에 값을 넣어 잘리게 두는 것 (안 들어가면 막대 밖 고정 칸으로)

## 이 킷에만 해당 (금지 보강)
- 상대 uplift(`+30.8%`)와 절대 delta(`+1.6%p`)를 한 칸에 섞는 것
- 데이터가 뒷받침하지 않는 SRM·Guardrail 경고를 남겨두는 것 (χ² p<0.01 아니면 SRM으로 쓰지 않는다)

## 작업이 끝나면
- `output/abtest_dashboard.html`로 저장
- 브라우저로 열 수 있는 절대경로 링크를 안내
- 마지막에 "배포 권고 1줄 요약"을 텍스트로도 출력 (어느 Variant를 배포할지)

