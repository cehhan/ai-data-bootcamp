# 코호트 리텐션 & LTV 대시보드 킷

구독 데이터(CSV) 하나만 있으면, **명령어 한 줄**로 강사와 동일한 퀄리티의 리텐션 대시보드가 만들어집니다.

## 사용법 (3단계)

```bash
# 1. 이 폴더에서 Claude Code 실행
cd 02-retention
claude

# 2. 명령어 한 줄
/build-dashboard

# 3. 끝. output/retention_dashboard.html 이 열립니다.
```

## 내 데이터로 바꾸기
`data/subscriptions.csv`를 본인 구독 데이터로 교체하고 다시 `/build-dashboard` 하면 끝.
필요한 컬럼: `user_id, signup_month, active_month, mrr, churned` (+ 선택 `plan`)
- `signup_month` = 가입월(코호트), `active_month` = 그 유저가 활성이었던 월
- `churned` = 그 달 이탈했으면 1, 아니면 0

## 폴더 구조
```
02-retention/
├── CLAUDE.md                       # 디자인 헌법 (색·KPI·What-if 규칙)
├── .claude/skills/build-dashboard/ # 작업 절차 (이게 명령어가 됨)
├── templates/reference.html        # 품질 기준 = 강사의 완성 대시보드
├── data/subscriptions.csv          # 샘플 데이터 (여기를 교체)
└── output/                         # 결과물이 여기 생성됨
```

## 무엇을 보여주나
- **코호트 리텐션 히트맵** — 가입월 × 경과월 잔존율 매트릭스
- **MRR 구성 추이** — 신규 / 확장 / 이탈 MRR 스택 + 성장률
- **What-if 시뮬레이터** — churn·expansion·신규 가정을 바꾸면 MRR/NRR이 어떻게 움직이는지
- **LTV 분포 · 이탈 사유 Pareto · 플랜 세그먼트 표**

## 왜 강사와 똑같이 나오나?
- **CLAUDE.md** = 디자인·KPI·What-if 규칙을 고정 (헌법)
- **Skill** = 코호트 계산 → 렌더 절차를 고정 (작업 매뉴얼)
- **templates/reference.html** = 품질 기준선 (이걸 보고 같은 수준으로 만듦)

세 개가 묶여 있어서, 데이터만 바뀌어도 결과 퀄리티는 일정합니다.
