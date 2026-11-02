"""모형별 모자란 인원·비용과 남는 인원·비용 (2025년 원점 12개, 실제 휴관일 제외).

    python scripts/shortage_by_model.py

output/ 의 예측 파일 전부를 읽어서, 모형마다 두 가지 규칙으로 계산합니다.
- 권고 규칙: 올림, 영업일 최소 1명 (근무표 기준)
- 소수: 예측 ÷ 2,000명 그대로 (올림 전 이론값)

결과: results/모형별_모자람_남음.csv
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

RESULTS = ROOT / "results"
BASE = "직전7일평균"


def load_all_predictions():
    files = sorted(OUTPUT_DIR.glob("pred_*.csv"))
    if not files:
        sys.exit("예측 파일이 없습니다. 먼저 run_classic.py 등을 실행하세요.")
    pred = pd.concat([pd.read_csv(f, parse_dates=["origin", "date"]) for f in files], ignore_index=True)
    return pred.drop_duplicates(subset=["model", "origin", "site", "date"], keep="first")


def main():
    pred = load_all_predictions()
    data = load_train()[["site", "date", "total", "actual_closed", "planned_closed"]]
    m = pred.merge(data, on=["site", "date"])
    m = m[m.actual_closed == 0]

    rows = []
    for rule in ["권고 규칙", "소수"]:
        base_cost = cost_parts(m[m.model == BASE], rule)["총 비용(원)"]
        for name in sorted(m.model.unique()):
            r = cost_parts(m[m.model == name], rule)
            rows.append({"규칙": rule, "모형": name, **r,
                         "직전 7일 평균 대비 절감(원)": base_cost - r["총 비용(원)"],
                         "직전 7일 평균 대비 절감 비율(%)": round((base_cost - r["총 비용(원)"]) / base_cost * 100, 1)})

    table = pd.DataFrame(rows)
    table = table.sort_values(["규칙", "총 비용(원)"], ascending=[False, True]).reset_index(drop=True)
    pd.set_option("display.width", 240)
    print(table.to_string(index=False))
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "모형별_모자람_남음.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {RESULTS / '모형별_모자람_남음.csv'}")


if __name__ == "__main__":
    main()
