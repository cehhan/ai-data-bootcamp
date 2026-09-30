# DI 분석 파이프라인

일곱 개의 전문 에이전트를 순서대로 지휘하는 **오케스트레이터**입니다.

@.claude/rules/analysis-principles.md
@.claude/rules/metric-definition.md
@.claude/rules/design-system.md

---

## 파이프라인

```
@data-ingestion → @eda → @problem → @metrics → @analysis → @dashboard → @report
```

| 단계 | 에이전트 | 산출물 |
|---|---|---|
| 1 | `@data-ingestion` | `01_dataset_profile.md` |
| 2 | `@eda` | `02_eda_report.md` |
| 3 | `@problem` | `03_problem_definition.md` |
| 4 | `@metrics` | `04_kpi_summary.md` |
| 5 | `@analysis` | `05_analysis_report.md` |
| 6 | `@dashboard` | `06_dashboard.html` |
| 7 | `@report` | `07_executive_report.md` |

분석 감사는 단계가 아니라 도구입니다. `/audit-analysis`로 언제든 부릅니다.

---

## 입력 — 둘 다 있어야 시작한다

```
runs/latest/input/
├── <데이터 파일>      데이터
└── 00_context.md      사람이 쓴 분석 의도
```

**`00_context.md` 가 없으면 파이프라인을 시작하지 않는다.**
데이터만으로는 "무엇을 해결해야 하는가"를 알 수 없다. 데이터에서 문제를 역산하면
그럴싸하지만 아무 결정과도 무관한 분석이 나온다.

## 폴더 규약

- **작업 폴더는 항상 `runs/latest/` 다.** 경로를 하나만 기억한다
- 원본 데이터와 컨텍스트는 `runs/latest/input/` 에만 있다
- 산출물은 `runs/latest/outputs/` 에 저장한다
- 수치를 만든 계산 스크립트와 그 출력은 `runs/latest/queries/` 에 저장한다
- 새 실행을 시작할 때 이전 실행은 `runs/<타임스탬프>/` 로 보관된다. 보관 폴더는 지우지 않는다
- 그 밖의 위치에 파일을 만들지 않는다. 임시 파일은 `/tmp` 를 쓴다

## 산출물 파일명

`NN_이름.md` 형식. 번호는 실행 순서다.
번호를 붙이는 이유: 어느 단계까지 진행됐는지 폴더만 보고 알 수 있어야 한다.

## 모델

| 작업 | 모델 |
|---|---|
| 구조 파악 · 탐색 · 문제 정의 · 지표 정의 · 검증 · 보고서 요약 | `claude-haiku-4-5` |
| 대시보드 제작 | `claude-sonnet-4-5` |

대시보드만 상위 모델을 쓰는 이유: 앞 단계는 정해진 형식으로 사실을 옮기는 일이라
작은 모델로 충분하다. 대시보드는 레이아웃 판단과 SVG 좌표 계산을 함께 해야 해서 다르다.

이 배분이 품질을 해치는 지점은 03·05(판단이 가장 많은 단계)일 가능성이 높다.
완주 시 그 두 단계의 산출물 품질을 별도로 기록한다.

## 언어

산출물은 한국어로 쓴다. 컬럼명·코드·파일명은 원문 그대로 둔다.

## 하지 말 것

- 파이프라인 전체 재실행. 문제가 있으면 그 단계만 다시 돌린다
- `runs/` 폴더 삭제. 앞 단계 산출물은 다음 단계의 입력이고 체크포인트다
- 앞 단계 산출물을 읽지 않고 원본 데이터부터 다시 읽는 것
- 에이전트끼리 대화. 소통은 파일로만 한다

---

## 시작 방법

```
1. runs/latest/input/ 에 데이터 파일과 00_context.md 를 넣는다
2. /run-pipeline
```

개별 단계만: `"@eda 다시 실행해줘"`
분석 감사만: `/audit-analysis`
