"""통계 모형 (ETS, ARIMA, SARIMA, Prophet) 을 계산하고 결과를 저장합니다.

    python scripts/run_stat.py
결과: output/pred_stat.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import evaluate  # noqa: E402
from forecast_fva.stat_models import predict_stat  # noqa: E402


def main():
    df = load_train()
    pred = predict_stat(df)
    OUTPUT_DIR.mkdir(exist_ok=True)
    pred.to_csv(OUTPUT_DIR / "pred_stat.csv", index=False, encoding="utf-8-sig")
    summary, _ = evaluate(pred, df)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
