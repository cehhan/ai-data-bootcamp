"""기준 · 서비스 수준 보정 · 배율 모형(행 3~7, 배율+월) · LightGBM 을 계산하고 결과를 저장합니다.

    python scripts/run_classic.py
결과: output/pred_classic.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from forecast_fva.baseline import predict_baseline  # noqa: E402
from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import evaluate  # noqa: E402
from forecast_fva.lgbm_model import predict_lgbm  # noqa: E402
from forecast_fva.regression import predict_regression  # noqa: E402


def main():
    df = load_train()
    pred = pd.concat([predict_baseline(df), predict_regression(df), predict_lgbm(df)], ignore_index=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    pred.to_csv(OUTPUT_DIR / "pred_classic.csv", index=False, encoding="utf-8-sig")
    summary, _ = evaluate(pred, df)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
