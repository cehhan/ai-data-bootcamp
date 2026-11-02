"""LightGBM 분위수 모형 (0.8 분위수). 원점마다 원점 전날까지의 데이터로 학습합니다."""
import numpy as np
import pandas as pd

from .config import ORIGINS

FEATS = ["site_c", "dow", "month", "is_holiday", "is_weekend", "is_regular_closed_wd",
         "closed_wd_holiday", "closure_shifted", "is_myeongjeol", "myeongjeol_len",
         "seollal_offset", "chuseok_offset", "is_last_wednesday"]


def predict_lgbm(df, origins=ORIGINS):
    import lightgbm as lgb

    d = df.copy()
    d["dow"] = d.date.dt.weekday
    d["site_c"] = d.site.astype("category")
    parts = []
    for origin in origins:
        end = origin + pd.offsets.MonthBegin(1)
        hist = d[(d.date < origin) & (d.actual_closed == 0) & (d.total > 0)]
        tgt = d[(d.date >= origin) & (d.date < end)].copy()
        if tgt.empty:
            continue
        model = lgb.LGBMRegressor(objective="quantile", alpha=0.8, n_estimators=300,
                                  learning_rate=0.05, num_leaves=31, min_child_samples=40,
                                  random_state=42, verbose=-1)
        model.fit(hist[FEATS], np.log(hist.total))
        tgt["pred"] = np.exp(model.predict(tgt[FEATS]))
        tgt["origin"] = origin
        tgt["model"] = "LightGBM 0.8 분위수"
        parts.append(tgt[["model", "origin", "site", "date", "pred"]])
    return pd.concat(parts, ignore_index=True)
