"""학습 데이터 불러오기."""
import pandas as pd

from .config import DATA_PATH


def load_train(path=DATA_PATH):
    """날짜 × 개소 표 (2023-01-01 ~ 2025-12-31, 25,208행)."""
    return pd.read_csv(path, parse_dates=["date"], encoding="utf-8-sig")
