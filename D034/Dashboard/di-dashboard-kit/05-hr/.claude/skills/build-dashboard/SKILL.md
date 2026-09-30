---
name: build-dashboard
description: data/의 채용 퍼널(recruiting.csv)과 직원 단위(employees.csv) 두 CSV를 집계·분석해, templates/reference.html과 동일한 퀄리티의 HR 채용 퍼널·People Analytics 대시보드를 output/에 생성하는 스킬. "대시보드 만들어줘", "/build-dashboard" 시 사용.
argument-hint: "[채용 CSV 경로] [직원 CSV 경로] — 생략 시 data/recruiting.csv, data/employees.csv"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Bash
---

# build-dashboard — HR 대시보드 자동 생성

수강생이 이 명령 하나만 치면, 강사 퀄리티의 채용 퍼널·People Analytics 대시보드가 자기 데이터로 나온다.
**반드시 아래 5단계를 순서대로 수행한다. 단계를 건너뛰지 않는다.**

## STEP 1 — 데이터 읽기 (EDA · 2개 소스)
- 인자로 받은 CSV(없으면 `data/recruiting.csv`, `data/employees.csv`)를 로드.
  **직원 파일은 수천 행이므로 행을 다 읽지 말고 python(pandas)으로 집계**한다.
- 두 소스의 컬럼·행 수·부서 목록·기간을 각각 한 줄로 요약해 사용자에게 보여준다.
- 필수 컬럼 확인 — **없으면 진행하지 말고 사용자에게 알린다.**
  - `recruiting.csv`: `department, stage, stage_order, candidates, passed, source, avg_days`
  - `employees.csv`: `employee_id, department, tenure_years, perf_grade, engagement, last_1on1_days, status, leave_type, leave_month, risk_score`
  - 컬럼명이 다르면 가장 가까운 것에 매핑하고, 매핑 결과를 알려준다.
- 퍼널 단계 수는 데이터의 `stage_order`를 따른다. 레퍼런스가 5단계여도 데이터가 6단계면 **6단계로 그린다.**

## STEP 2 — 지표 계산 (실제 숫자)
`CLAUDE.md`의 계산식대로 계산한다. 계산은 Bash(python)로 실제 수행하고, 결과 수치를 표로 한 번 보여준다. **추정·반올림 임의값 금지.**

**채용(ATS) — `recruiting.csv`**
- 단계별 통과율 = `passed / candidates × 100`, 단계 이탈률 = `100 − 통과율`. **최저 통과율 단계가 병목.**
- 퍼널 전체 전환율 = 마지막 단계 `passed` / 첫 단계 `candidates × 100`.
- time-to-hire = 부서별 `avg_days` 합(누적). 전체는 부서 평균.
- **오퍼 수락률 = `오퍼` 단계의 `passed / candidates × 100`** (별도 `offer_sent/offer_accepted` 컬럼은 쓰지 않는다).

**직원(HRIS) — `employees.csv`**
- 총 재직 인원 = `count(status=재직)` · 자발적 퇴사자 = `count(leave_type=자발)`.
- 자발적 이직률 = 자발 퇴사 / 재직 × 100. **부서별로도 산출하되, 부서 분모가 30명 미만이거나 분자가 5명 미만이면 카드에 `표본 작음` 주석을 붙인다.**
- 이직 위험 등급 = `risk_score` 구간 — 매우위험 ≥70 · 위험 50~69 · 주의 30~49 · 안정 <30. 각 구간 인원수와 비중.
- 고위험 이탈 인원 = `count(status=재직 AND risk_score ≥ 70)`.
- 성과 등급 분포 = `perf_grade`(S~D) 집계.
- Q1 인원 변동 = 입사(`recruiting` 입사 단계 `passed` 합) − 자발 퇴사 − 비자발 퇴사.

## STEP 3 — 레퍼런스 구조 흡수
- `templates/reference.html`을 **반드시 Read** 한다.
- HTML 골격(사이드바, KPI 카드 6개 + `spark0~5`, STEP 1~4 섹션), CSS 토큰(`:root`), chart.js·canvas 초기화 패턴을 파악한다.
- 교체 대상을 정확히 확인한다:

| 대상 | 위치(레퍼런스 기준) | 무엇을 채우나 |
|---|---|---|
| KPI 6개 + `spark0~5` | 상단 카드 | 총 재직·신규 입사·자발 퇴사·고위험 인원·평균 채용 소요일·자발적 이직률 + 각 7포인트 추이 배열 |
| `depts` (618~626줄) | 부서별 채용 소요일 추이 (`trendChart`) | `{label, color, data[]}` — 부서별 time-to-hire 시계열 |
| `headcountSpark` | Q1 인원 변동 | 입사/퇴사 분해 |
| `.risk-dist` 블록 | 이직 위험도 등급 분포 | 등급별 인원·비중 |
| 부서별 자발적 이직률 막대 | ROW 3 좌 | 부서별 % (내림차순) |
| Q1 채용 퍼널 | ROW 3 중 | 단계별 인원·누적 전환율 |
| `perfChart` | 성과 등급 분포 | S~D 인원 |
| `aiItems` (717줄) | AI People 알림 & 액션 | 병목 단계·고위험 부서·개입 대상 |
| `riskData` (746줄) | 이탈 위험 인원 테이블 | 상위 위험 직원 |

- **`riskData`의 `perf` 필드에는 데이터의 `perf_grade` 등급(S~D)을 그대로 넣는다.** 점수로 임의 변환하지 않는다.
- 스파크라인은 `drawSparkline(id, [배열], color)` 형태로 **실제 계산 배열을 넣는다.** 난수 생성 금지.
- 이 구조를 그대로 재사용한다 — 새로 디자인하지 않는다.

## STEP 4 — 데이터 주입해서 렌더
- 레퍼런스 구조 위에 STEP 2의 **실제 계산값**을 채워 `output/hr_dashboard.html` 생성.
- const 배열은 **값만** 교체 — 필드명·형식·JS 로직은 절대 건드리지 않는다(안 그러면 차트 깨짐).
- 이름은 `김○○` 처럼 **마스킹**한다. 실명·사번을 그대로 노출하지 않는다.
- 제목·기준 기간을 데이터 기간으로 갱신. KPI 수치는 검정(`--t1`) 고정, 색은 위험도·증감 뱃지에만.
- 색은 `:root` 토큰(`--red:#ef7d86`, `--amber:#f59e0b`, `--green:#35c995`)만 쓴다. 토큰 밖의 색을 새로 만들지 않는다.
- 위험 등급은 **색만으로 구분하지 않는다** — 등급 라벨(매우위험/위험/주의/안정)을 항상 함께 표기.
- `CLAUDE.md`의 금지 항목(한쪽 border, 수치 색 남용, 장식, 필드명 변경)을 위반하지 않았는지 자체 점검.

## STEP 5 — 전달
- 저장 경로의 **절대경로 file:// 링크**를 안내한다.
- "이번 데이터 기준 요약"을 3줄 이내로 출력 — **어느 단계가 병목인지 / 어느 부서가 위험한지 / 누구를 먼저 붙잡을지.**
- 표본이 작아 주석을 붙인 지표가 있으면 그 사실을 함께 알린다.
- 끝에 한 줄: "data/의 CSV를 본인 데이터로 바꾸고 다시 `/build-dashboard` 하면 같은 퀄로 재생성됩니다."

## 핵심 원칙
- reference = 품질 기준선. 결과가 그보다 단순/다른 톤이면 다시 만든다.
- 복붙이 아니라 "구조 재사용 + 데이터 교체". 숫자는 항상 실제 분석값.
- **레퍼런스의 숫자는 디자인용 예시다.** 산출물에 레퍼런스 숫자가 하나라도 남아 있으면 실패다.
- 개인 정보를 다루므로 이름 마스킹과 "예측 점수는 개입의 근거이지 평가가 아니다"라는 맥락을 유지한다.
