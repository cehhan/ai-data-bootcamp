---
name: build-dashboard
description: data/의 실험 CSV를 분석해, templates/reference.html과 동일한 퀄리티의 A/B 테스트 의사결정 대시보드를 output/에 생성하는 스킬. "대시보드 만들어줘", "/build-dashboard" 시 사용.
argument-hint: "[CSV 경로 — 생략 시 data/experiments.csv]"
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Bash
---

# build-dashboard — A/B 테스트 대시보드 자동 생성

수강생이 이 명령 하나만 치면, 강사 퀄리티의 A/B 테스트 대시보드가 자기 실험 데이터로 나온다.
**반드시 아래 5단계를 순서대로 수행한다. 단계를 건너뛰지 않는다.**

## STEP 1 — 데이터 읽기 (EDA)
- 인자로 받은 CSV(없으면 `data/experiments.csv`)를 Read/Bash로 로드.
- 컬럼·행 수·실험 목록·변형(A/B)·세그먼트를 한 줄로 요약해 사용자에게 보여준다.
- 필수 컬럼 확인: `experiment, variant, segment, users, conversions, revenue, runtime_days, guardrail`.
  - `variant`는 A(Control)·B(Variant) 두 값. 컬럼명이 다르면 가장 가까운 것에 매핑하고, 매핑 결과를 알려준다.
  - 각 실험이 A·B 쌍을 갖는지, 세그먼트별로 쪼개져 있는지 확인.

## STEP 2 — A/B 통계 계산 (실제 숫자)
- `CLAUDE.md`의 계산식대로 실험별 + 세그먼트별로 계산한다.
  1. 변형별 **전환율** CVR = conversions / users (A=Control, B=Variant).
  2. **절대 차이** Δ = CVR(B) − CVR(A) (`%p`), **상대 Uplift** = Δ / CVR(A) (`%`).
  3. **z-test로 p-value**: SE = √(p_a(1−p_a)/n_a + p_b(1−p_b)/n_b), z = (p_b−p_a)/SE, p = 양측.
  4. **95% 신뢰구간**: Δ ± 1.96·SE → 상대 uplift 기준 [lo, hi]로 환산.
  5. **유의성** sig = (p < 0.05). **decision**은 CLAUDE.md 규칙(ship/hold/retest/monitor/stop)으로.
- 실험을 **상대 Uplift 내림차순**으로 정렬. ship 후보·stop 대상을 식별.
- 계산은 Bash(python)로 실제 수행하고, 결과 수치를 표로 한 번 보여준다. **추정·반올림 임의값 금지.**
- `%`와 `%p`, 상대 uplift와 절대 delta를 표에서부터 분리해 표기한다.

## STEP 3 — 레퍼런스 구조 흡수
- `templates/reference.html`을 **반드시 Read** 한다.
- HTML 골격(사이드바, KPI 6카드, 차트 wrap, Forest Plot SVG, 표), CSS 토큰, chart.js 초기화 패턴을 파악한다.
- 교체 대상은 데이터 배열뿐임을 확인한다: `tableData`, `forestData`, `segData`, `aiItems`.
  누적차이 라인은 `tableData`에서 `CUMEXPS`로 자동 파생되므로 별도 배열이 없다.
- 품질 경고 패널(`.warn-list`)은 하드코딩 HTML이다. SRM(χ² p<0.01)·AOV 악화·표본 부족·다중비교(BH)를 **데이터로 실제 판정**해 문구·수치를 교체하고, 해당 없으면 항목을 지운다.
- 이 구조를 그대로 재사용한다 — 새로 디자인하지 않고, JS 로직·차트 옵션은 건드리지 않는다.

## STEP 4 — 데이터 주입해서 렌더
- 레퍼런스 구조 위에 STEP 2의 **실제 계산값**을 채워 `output/abtest_dashboard.html` 생성.
- 레퍼런스 HTML을 읽어 `const tableData=`, `const forestData=`, `const segData=`, `const aiItems=`를 **정규식으로 교체**한다. `CUMEXPS`·`genCum`·`srnd`는 건드리지 않는다.
  - 필드명·형식을 레퍼런스와 **100% 동일**하게 유지(예: forestData는 `{name,effect,ci:[lo,hi],n,sig,decision}`).
  - 상단 KPI 6개, 제목/날짜(topbar meta, 사이드바 footer)도 새 값으로.
- KPI 수치는 검정 고정. decision 색은 `decisionColors` 그대로.
- `CLAUDE.md`의 금지 항목(한쪽 border, 수치 색, 장식, %/%p 혼용)을 위반하지 않았는지 자체 점검.

## STEP 5 — 전달 + 의사결정 권고
- 저장 경로의 **절대경로 file:// 링크**를 안내한다.
- "이번 실험 기준 배포 권고"를 3줄 이내로 요약 출력:
  - **배포(Ship)**: 어느 실험의 Variant(B)를 배포할지 + 근거(uplift·p·CI).
  - **중단/보류**: 어떤 실험을 stop/monitor 할지 + 이유(미유의·guardrail·표본부족).
  - **추가 검증**: retest/표본 연장 대상.
- 끝에 한 줄: "data/의 CSV를 본인 실험 데이터로 바꾸고 다시 `/build-dashboard` 하면 같은 퀄로 재생성됩니다."

## 핵심 원칙
- reference = 품질 기준선. 결과가 그보다 단순/다른 톤이면 다시 만든다.
- 복붙이 아니라 "구조 재사용 + 데이터 교체". 숫자는 항상 실제 통계 계산값.
- 통계적 유의성 없이 "좋아졌다"고 말하지 않는다. p-value·CI·표본을 항상 함께 보여준다.
