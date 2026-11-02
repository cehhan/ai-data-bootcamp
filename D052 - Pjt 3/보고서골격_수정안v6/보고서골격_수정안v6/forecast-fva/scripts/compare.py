"""output/ 의 예측 파일을 모두 읽어 같은 기준으로 비교표를 만듭니다.

    python scripts/compare.py
먼저 run_classic.py, run_stat.py, run_chronos.py 를 실행해 예측 파일을 만들어야 합니다.
결과: output/compare_summary.csv, output/compare_per_origin.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import evaluate  # noqa: E402


def main():
    files = sorted(OUTPUT_DIR.glob("pred_*.csv"))
    if not files:
        sys.exit("예측 파일이 없습니다. scripts/run_classic.py 등을 먼저 실행하세요.")
    pred = pd.concat([pd.read_csv(f, parse_dates=["origin", "date"]) for f in files], ignore_index=True)
    summary, per_origin = evaluate(pred, load_train())
    print(summary.to_string(index=False))
    summary.to_csv(OUTPUT_DIR / "compare_summary.csv", index=False, encoding="utf-8-sig")
    per_origin.round(0).to_csv(OUTPUT_DIR / "compare_per_origin.csv", encoding="utf-8-sig")
    print(f"\n저장: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
