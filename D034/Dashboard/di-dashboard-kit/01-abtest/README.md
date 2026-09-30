# A/B 테스트 실험 결과 대시보드 킷

실험 데이터(CSV) 하나만 있으면, **명령어 한 줄**로 강사와 동일한 퀄리티의 A/B 테스트 의사결정 대시보드가 만들어집니다.

## 사용법 (3단계)

```bash
# 1. 이 폴더에서 Claude Code 실행
cd 01-abtest
claude

# 2. 명령어 한 줄
/build-dashboard

# 3. 끝. output/abtest_dashboard.html 이 열립니다.
```

## 내 데이터로 바꾸기
`data/experiments.csv`를 본인 실험 데이터로 교체하고 다시 `/build-dashboard` 하면 끝.
필요한 컬럼: `experiment, variant(A/B), segment, users, conversions, revenue, runtime_days, guardrail`
- `variant`는 A=Control, B=Variant 두 값. 각 실험을 A·B 쌍으로, 세그먼트별로 나눠 넣으면 됩니다.

## 무엇이 나오나
- 누적 전환율 차이 + 95% 신뢰구간 라인
- 실험별 효과크기 Forest Plot (uplift × CI × 유의성)
- 세그먼트 분석 버블 차트 (uplift × 신뢰도 × 표본)
- 실험 의사결정 테이블 (Absolute Δ · Relative Uplift · p-value · Decision)
- "어느 Variant를 배포할지" 의사결정 권고

## 폴더 구조
```
01-abtest/
├── CLAUDE.md                       # 디자인 헌법 (색·KPI·통계 규칙)
├── .claude/skills/build-dashboard/ # 작업 절차 (이게 명령어가 됨)
├── templates/reference.html        # 품질 기준 = 강사의 완성 대시보드
├── data/experiments.csv            # 샘플 데이터 (여기를 교체)
└── output/                         # 결과물이 여기 생성됨
```

## 왜 강사와 똑같이 나오나?
- **CLAUDE.md** = 디자인·KPI·통계 규칙을 고정 (헌법)
- **Skill** = 분석(z-test·CI)→렌더 절차를 고정 (작업 매뉴얼)
- **templates/reference.html** = 품질 기준선 (이걸 보고 같은 수준으로 만듦)

세 개가 묶여 있어서, 데이터만 바뀌어도 결과 퀄리티는 일정합니다.
