# PM 지표 위계 대시보드 킷

프로덕트 지표 데이터(CSV) 하나만 있으면, **명령어 한 줄**로 강사와 동일한 퀄리티의 지표 위계·원인 분석 대시보드가 만들어집니다.

## 사용법 (3단계)

```bash
# 1. 이 폴더에서 Claude Code 실행
cd 03-pm
claude

# 2. 명령어 한 줄
/build-dashboard

# 3. 끝. output/pm_dashboard.html 이 열립니다.
```

## 내 데이터로 바꾸기
`data/user_events.csv`를 본인 이벤트 로그로 교체하고 다시 `/build-dashboard` 하면 끝.
샘플은 **1,228명 · 13주(2024-04-01~06-30) · 8,571행**입니다 — 주간 코호트 13개라 리텐션 곡선이 통계적으로 의미를 갖습니다.
필요한 컬럼: `user_id, event_date, event, plan, segment`
`event` 값은 `signup · login · trial_start · payment · cancel · search_fail` 입니다 (유저 단위 이벤트 로그라야 코호트·RFM·이탈 분석이 나옵니다).
(이벤트에서 파생되는 지표: 재결제율 · 구독전환율 · 체험전환율 · 좌절경험률 · 액티브리텐션 · 코호트 리텐션 · RFM 세그먼트 · 이탈 시점/사유)

## 폴더 구조
```
03-pm/
├── CLAUDE.md                       # 디자인 헌법 (색·지표 위계·정의·구성 규칙)
├── .claude/skills/build-dashboard/ # 작업 절차 (이게 명령어가 됨)
├── templates/reference.html        # 품질 기준 = 강사의 완성 대시보드
├── data/user_events.csv           # 샘플 유저 이벤트 로그 (여기를 교체)
└── output/                         # 결과물이 여기 생성됨
```

## 무엇을 보여주나 (STEP 흐름)
- **STEP 1** — 핵심 지표 6개 한눈에 (지금 어디가 문제인가?)
- **STEP 2** — 지표 구조: North Star → Primary → Input → Guardrail 위계 트리
- **STEP 3** — 이탈 분석: 누가(RFM 세그먼트) / 언제(이탈 시점) / 왜(사유 TOP5)
- **STEP 4** — 액션 플랜: 우선순위 인사이트 + 계층별 Input Metric 상태

## 왜 강사와 똑같이 나오나?
- **CLAUDE.md** = 디자인·지표 정의·위계 규칙을 고정 (헌법)
- **Skill** = 분석→렌더 절차를 고정 (작업 매뉴얼)
- **templates/reference.html** = 품질 기준선 (이걸 보고 같은 수준으로 만듦)

세 개가 묶여 있어서, 데이터만 바뀌어도 결과 퀄리티는 일정합니다.
