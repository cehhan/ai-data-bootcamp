"""FVA 표 (가이드 요구사항 6): 단계를 하나씩 더할 때 비용이 얼마나 줄었는지 보는 표.

    python scripts/fva_table.py

단계 (행 번호는 보고서 4-4 기준)
- 행 1: 직전 7일 평균 (기준)
- 행 2: 서비스 수준 보정
- 행 3~7: 배율 모형, 피처를 한 줄씩 추가 (행 7은 이웃 궁 휴관까지 포함)
- 최종: 앙상블 (Chronos-2 + 달력과 Prophet 평균)
- 참고: 배율+월 (행 6 + 월 효과). 연쇄에는 넣지 않고 따로 표시

두 가지 기준으로 계산합니다.
- 권고 규칙: 올림, 영업일 최소 1명 (근무표 기준, 본문 기준)
- 소수: 예측 ÷ 2,000명 그대로 (올림 전 이론값)

차이 열: 바로 앞 단계 대비 비용 변화 (음수 = 줄어듦)
입력: output/pred_classic.csv, output/pred_ensemble.csv
결과: results/FVA_표.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402

from backtest_cost import cost_parts  # noqa: E402
from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import evaluate  # noqa: E402

RESULTS = ROOT / "results"

CHAIN = [
    ("행 1", "직전7일평균", "직전 7일 평균 (기준)"),
    ("행 2", "서비스수준보정", "서비스 수준 보정"),
    ("행 3", "배율 행3", "배율: 개소 수준"),
    ("행 4", "배율 행4", "배율: + 요일·정기 휴관"),
    ("행 5", "배율 행5", "배율: + 공휴일·명절"),
    ("행 6", "배율 행6", "배율: + 무료 개방일"),
    ("행 7", "배율 행7", "배율: + 이웃 궁 휴관"),
    ("최종", "앙상블(Chronos+Prophet)", "앙상블 (Chronos-2 + 달력과 Prophet 평균)"),
]
EXTRA = ("참고", "배율+월 (행6)", "배율: 행 6 + 월 효과 (연쇄 밖)")


def main():
    classic = pd.read_csv(OUTPUT_DIR / "pred_classic.csv", parse_dates=["origin", "date"])
    ens = pd.read_csv(OUTPUT_DIR / "pred_ensemble.csv", parse_dates=["origin", "date"])
    pred = pd.concat([classic, ens[["origin", "site", "date", "pred", "model"]]], ignore_index=True)

    tr = load_train()
    data = tr[["site", "date", "total", "actual_closed", "planned_closed"]]
    m = pred.merge(data, on=["site", "date"])
    m = m[m.actual_closed == 0]

    summary, _ = evaluate(pred, tr)
    wape_map = dict(zip(summary.model, summary.wape))

    # 가이드 기본 가정: 인력 수는 올림하지 않고 소수 그대로 계산 → 기본 비용은 소수 기준
    rows = []
    base_frac = None
    prev_frac = None
    for step, model, label in CHAIN + [EXTRA]:
        g = m[m.model == model]
        cost_f = cost_parts(g, "소수")["총 비용(원)"]
        cost_r = cost_parts(g, "권고 규칙")["총 비용(원)"]
        if base_frac is None:
            base_frac = cost_f
        saved_base = base_frac - cost_f
        diff = None if (step == "참고" or prev_frac is None) else cost_f - prev_frac
        if step != "참고":
            prev_frac = cost_f
        rows.append({
            "단계": step, "모형": label,
            "총 비용 소수(원)": cost_f,
            "앞 단계 대비 차이(원)": diff,
            "직전 7일 평균 대비 절감(원)": saved_base,
            "직전 7일 평균 대비 절감 비율(%)": round(saved_base / base_frac * 100, 1),
            "WAPE(%)": wape_map.get(model),
            "참고: 총 비용 권고 규칙(원)": cost_r,
        })

    table = pd.DataFrame(rows)
    pd.set_option("display.width", 240)
    print(table.to_string(index=False))
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "FVA_표.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {RESULTS / 'FVA_표.csv'}")


if __name__ == "__main__":
    main()
