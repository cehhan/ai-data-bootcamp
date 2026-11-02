"""누수 테스트: 예측이 원점 이전 데이터만 쓰는지 확인합니다.

    python tests/test_leakage.py

검사 내용
1. 미래 교란: 원점 이후의 관람객(total)과 실제 휴관 여부(actual_closed)를 무작위로 바꿔도
   예측값이 그대로여야 합니다. 바뀌면 미래 정보를 쓰고 있는 것입니다.
2. 과거 감도: 원점 이전의 관람객을 바꾸면 예측값이 달라져야 합니다.
   이 검사가 실패하면 1번 검사가 아무것도 확인하지 못하는 상태입니다.
3. 입력 열 점검: 모형 입력 열에 결과 값(관람객, 휴관 여부 등)이 들어 있지 않아야 합니다.

검사 대상: 베이스라인, 배율 모형(배율 행 3~7, 배율+월), LightGBM, ETS, ARIMA, SARIMA.
Prophet 과 Chronos-2 는 실행 시간이 길어서 이 검사에서는 뺐습니다(Colab에서 따로 확인).
검사 원점은 2025-07-01 하나입니다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecast_fva.baseline import base_forecasts  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.lgbm_model import FEATS, predict_lgbm  # noqa: E402
from forecast_fva.regression import feature_block, fit_predict  # noqa: E402
from forecast_fva.stat_models import predict_stat  # noqa: E402

ORIGIN = pd.Timestamp("2025-07-01")
END = ORIGIN + pd.offsets.MonthBegin(1)
FORBIDDEN = {"total", "actual_closed", "train_exclude", "row_missing", "paid", "free",
             "domestic", "foreign_en", "foreign_ja", "foreign_zh", "foreign_etc"}


def perturb_future(df, seed=0):
    """원점 이후의 관람객과 휴관 여부를 무작위 값으로 바꿉니다."""
    d = df.copy()
    rng = np.random.default_rng(seed)
    m = d.date >= ORIGIN
    d.loc[m, "total"] = rng.integers(0, 100_000, m.sum())
    d.loc[m, "actual_closed"] = rng.integers(0, 2, m.sum())
    return d


def perturb_past(df):
    """원점 이전 개방일의 관람객을 두 배로 바꿉니다."""
    d = df.copy()
    m = (d.date < ORIGIN) & (d.actual_closed == 0) & (d.total > 0)
    d.loc[m, "total"] = d.loc[m, "total"] * 2
    return d


def _baseline(d):
    bf = base_forecasts(d, ORIGIN).sort_values(["site", "date"])
    return bf[["last7", "naive", "snaive7"]].fillna(-1).values


def _regression(d, with_month):
    d = d.copy()
    d["dow"] = d.date.dt.weekday
    sites = sorted(d.site.unique())
    hist = d[(d.date < ORIGIN) & (d.actual_closed == 0) & (d.total > 0)]
    tgt = d[(d.date >= ORIGIN) & (d.date < END)].copy().sort_values(["site", "date"])
    cols = []
    for row in [3, 4, 5, 6, 7]:
        cols.append(fit_predict(hist, tgt, row, sites, with_month))
    return np.column_stack(cols)


def _lgbm(d):
    out = predict_lgbm(d, origins=[ORIGIN]).sort_values(["site", "date"])
    return out["pred"].values


def _stat(d, name):
    out = predict_stat(d, models=[name], origins=[ORIGIN]).sort_values(["site", "date"])
    return out["pred"].values


MODELS = {
    "베이스라인": _baseline,
    "배율 행3~7": lambda d: _regression(d, with_month=False),
    "배율+월": lambda d: _regression(d, with_month=True),
    "LightGBM": _lgbm,
    "ETS": lambda d: _stat(d, "ETS"),
    "ARIMA": lambda d: _stat(d, "ARIMA"),
    "SARIMA": lambda d: _stat(d, "SARIMA"),
}


def test_future_does_not_change_prediction(data):
    """1. 미래 교란: 예측값이 바뀌지 않아야 합니다."""
    bad = []
    perturbed = perturb_future(data)
    for name, fn in MODELS.items():
        a, b = fn(data), fn(perturbed)
        if not np.allclose(a, b, rtol=1e-7, atol=1e-6, equal_nan=True):
            bad.append(name)
    assert not bad, f"미래 값이 예측에 영향을 줍니다: {bad}"


def test_past_changes_prediction(data):
    """2. 과거 감도: 과거 값을 바꾸면 예측이 달라져야 합니다(검사가 작동하는지 확인)."""
    changed = perturb_past(data)
    not_changed = []
    for name, fn in MODELS.items():
        a, b = fn(data), fn(changed)
        if np.allclose(a, b, rtol=1e-7, atol=1e-6, equal_nan=True):
            not_changed.append(name)
    assert not not_changed, f"과거 값을 바꿔도 예측이 같습니다(검사 무효): {not_changed}"


def test_inputs_have_no_forbidden_columns(data):
    """3. 입력 열: 결과 값이 모형 입력에 들어 있지 않아야 합니다."""
    sites = sorted(data.site.unique())
    d = data.head(50).copy()
    d["dow"] = d.date.dt.weekday
    used = set(FEATS) | set(feature_block(d, 7, sites, with_month=True).columns)
    leaked = sorted(used & FORBIDDEN)
    assert not leaked, f"금지된 열이 모형 입력에 있습니다: {leaked}"


def main():
    data = load_train()
    checks = [
        ("1. 미래 교란", test_future_does_not_change_prediction),
        ("2. 과거 감도", test_past_changes_prediction),
        ("3. 입력 열 점검", test_inputs_have_no_forbidden_columns),
    ]
    failed = []
    for label, fn in checks:
        try:
            fn(data)
            print(f"통과: {label}")
        except AssertionError as e:
            failed.append(label)
            print(f"실패: {label} → {e}")
    if failed:
        sys.exit(1)
    print("\n누수 테스트 모두 통과")


if __name__ == "__main__":
    main()
