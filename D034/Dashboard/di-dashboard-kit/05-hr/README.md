# HR 채용 퍼널 & People Analytics 대시보드 킷

채용 데이터(CSV) 하나만 있으면, **명령어 한 줄**로 강사와 동일한 퀄리티의 대시보드가 만들어집니다.

## 사용법 (3단계)

```bash
# 1. 이 폴더에서 Claude Code 실행
cd 05-hr
claude

# 2. 명령어 한 줄
/build-dashboard

# 3. 끝. output/hr_dashboard.html 이 열립니다.
```

## 내 데이터로 바꾸기
`data/recruiting.csv`(채용)·`data/employees.csv`(직원)를 본인 데이터로 교체하고 다시 `/build-dashboard` 하면 끝.
필요한 컬럼
- `recruiting.csv`: `department, stage, stage_order, candidates, passed, source, avg_days`
- `employees.csv`: `employee_id, department, tenure_years, perf_grade, engagement, last_1on1_days, status, leave_type, leave_month, risk_score`
퍼널 단계는 `지원 → 서류 → 1차면접 → 2차면접 → 오퍼 → 입사` 순서로 stage_order에 넣습니다.

## 폴더 구조
```
05-hr/
├── CLAUDE.md                      # 디자인 헌법 (색·KPI·구성 규칙)
├── .claude/skills/build-dashboard/ # 작업 절차 (이게 명령어가 됨)
├── templates/reference.html       # 품질 기준 = 강사의 완성 대시보드 (HR People Analytics OS)
├── data/recruiting.csv            # 채용 퍼널 (부서×단계)
├── data/employees.csv             # 직원 단위 (재직·이직·성과·이탈위험)
└── output/                        # 결과물이 여기 생성됨
```

## 왜 강사와 똑같이 나오나?
- **CLAUDE.md** = 디자인·KPI 규칙을 고정 (헌법)
- **Skill** = 분석→렌더 절차를 고정 (작업 매뉴얼)
- **templates/reference.html** = 품질 기준선 (이걸 보고 같은 수준으로 만듦)

세 개가 묶여 있어서, 데이터만 바뀌어도 결과 퀄리티는 일정합니다.

## 이 대시보드가 답하는 질문
- 채용 퍼널의 **어느 단계가 병목**인가? (서류→면접 이탈률 등)
- **어느 부서**가 전환율이 가장 낮고 이직률이 높은가?
- 지금 **누구를 먼저 붙잡아야** 하는가? (이탈 위험 인원 조기 탐지)
