# di-pipeline-kit

CSV 하나와 **분석 의도 한 장**을 넣으면, 역할이 나뉜 에이전트 일곱 개가 차례로 처리해서
대시보드와 임원 보고서를 만들어 내는 작업 폴더입니다.

---

## 시작하기

터미널을 열고 **이 폴더 안에서** 실행합니다.

```bash
cd <이 폴더>
claude
```

Claude Code 가 켜지면:

```
/run-pipeline
```

`command not found: claude`가 나오면 터미널을 다시 열고 `claude doctor`로
설치 상태를 확인합니다.

## 시작 전에 파일 하나를 써야 합니다

**데이터만으로는 파이프라인이 시작되지 않습니다.**

```bash
cp runs/latest/input/00_context.md.template runs/latest/input/00_context.md
```

이 파일을 열어 다섯 항목을 채웁니다. 15줄이면 충분합니다.
가장 중요한 것은 **"어떤 결정을 앞두고 있는가"** 한 줄입니다.

`00_context.md` 가 없으면 파이프라인은 시작하지 않고 멈춥니다. **그게 정상 동작입니다.**
데이터에서 문제를 역산하면 그럴싸하지만 아무 결정과도 무관한 분석이 나옵니다.

## 포함된 구성

에이전트 일곱 개와 공통 규칙, 실행 Skill, 대시보드 템플릿이 들어 있습니다.
분석을 시작하기 전에 `CLAUDE.md`와 `.claude/`의 역할 구성을 확인하세요.

---

## 폴더

```
.
├── CLAUDE.md              이 프로젝트의 규칙. 실행할 때마다 항상 읽힌다
├── .claude/
│   ├── rules/             모든 에이전트에 공통인 원칙 3개
│   ├── agents/            에이전트 7개 — 파일 이름이 호출 이름이다
│   └── skills/            run-pipeline · audit-analysis · dashboard-design
├── templates/             대시보드 베이스
└── runs/latest/
    ├── input/             데이터 + 00_context.md   ← 여기서 시작
    ├── outputs/           01_~07_ 산출물이 여기 생긴다
    └── queries/           수치를 만든 계산 스크립트
```

## 일곱 단계

```
@data-ingestion → @eda → @problem → @metrics → @analysis → @dashboard → @report
```

| | 산출물 |
|---|---|
| 1 | `01_dataset_profile.md` |
| 2 | `02_eda_report.md` |
| 3 | `03_problem_definition.md` |
| 4 | `04_kpi_summary.md` |
| 5 | `05_analysis_report.md` |
| 6 | `06_dashboard.html` |
| 7 | `07_executive_report.md` |

**번호가 붙은 이유:** 폴더만 보면 어디까지 갔는지 알 수 있습니다.
`03` 까지 있고 `04` 가 없으면 4단계에서 멈춘 것입니다.

## 문제가 생기면

```bash
ls runs/latest/outputs/     # 없는 번호가 실패한 단계다
```

**전체를 다시 돌리지 마세요.** 없는 번호의 그 단계만 다시 부릅니다.

```
"@problem 다시 실행해줘"
```

## 하지 말 것

- **`runs/` 폴더 삭제.** 앞 단계 산출물이 다음 단계의 입력이고 체크포인트입니다
- **산출물을 손으로 고쳐 오류를 숨기기.** 문제가 있으면 해당 단계를 다시 실행합니다
- **민감한 데이터·API 키 입력.** 승인된 데이터만 사용합니다

## 분석 감사

파이프라인 실행 후 계산의 재현성, 문서 간 일관성, 표본 타당성과 규칙 준수를
점검하려면 다음 명령을 실행합니다.

```
/audit-analysis
```
