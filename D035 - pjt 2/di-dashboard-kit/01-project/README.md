# 마케팅 캠페인 성과 대시보드 킷

캠페인 데이터(CSV) 하나만 있으면, **명령어 한 줄**로 강사와 동일한 퀄리티의 대시보드가 만들어집니다.

## 사용법 (3단계)

```bash
# 1. 이 폴더에서 Claude Code 실행
cd 04-marketing
claude

# 2. 명령어 한 줄
/build-dashboard

# 3. 끝. output/marketing_dashboard.html 이 열립니다.
```

## 내 데이터로 바꾸기
`data/campaigns.csv`를 본인 캠페인 데이터로 교체하고 다시 `/build-dashboard` 하면 끝.
필요한 컬럼: `week, channel, impressions, clicks, conversions, spend, revenue`

## 폴더 구조
```
04-marketing/
├── CLAUDE.md                      # 디자인 헌법 (색·KPI·구성 규칙)
├── .claude/skills/build-dashboard/ # 작업 절차 (이게 명령어가 됨)
├── templates/reference.html       # 품질 기준 = 강사의 완성 대시보드
├── data/campaigns.csv             # 샘플 데이터 (여기를 교체)
└── output/                        # 결과물이 여기 생성됨
```

## 왜 강사와 똑같이 나오나?
- **CLAUDE.md** = 디자인·KPI 규칙을 고정 (헌법)
- **Skill** = 분석→렌더 절차를 고정 (작업 매뉴얼)
- **templates/reference.html** = 품질 기준선 (이걸 보고 같은 수준으로 만듦)

세 개가 묶여 있어서, 데이터만 바뀌어도 결과 퀄리티는 일정합니다.
