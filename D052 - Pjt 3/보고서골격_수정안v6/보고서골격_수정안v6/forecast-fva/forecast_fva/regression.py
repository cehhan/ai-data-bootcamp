"""배율 모형 (FVA 행 3~7) 과 행 6 + 월 효과.

행 3: 개소 수준          행 4: + 요일·정기 휴관(②)
행 5: + 공휴일·명절      행 6: + 무료 개방일(①, 개소별 배율)
행 7: + 이웃 궁 휴관(③)
배율+월: 행 6 피처에 월 더미(1월 기준 11개)를 추가

방식: 원점 전날까지의 로그 관람객을 선형 회귀로 맞추고,
      잔차의 0.8 분위수를 더해 예측합니다 (예측 = exp(회귀값 + 잔차 0.8 분위수)).
"""
import numpy as np
import pandas as pd

from .baseline import base_forecasts, service_ratio
from .config import ORIGINS, QUANTILE


def feature_block(df, row, sites, with_month=False):
    X = pd.DataFrame(index=df.index)
    for s in sites:
        X[f"site_{s}"] = (df.site == s).astype(float)
    if row >= 4:
        for d in range(1, 7):                                  # 월요일 기준 요일 더미
            X[f"dow_{d}"] = (df.dow == d).astype(float)
        X["is_regular_closed_wd"] = df.is_regular_closed_wd.astype(float)
        X["closed_wd_holiday"] = df.closed_wd_holiday.astype(float)
        X["closure_shifted"] = df.closure_shifted.astype(float)
    if row >= 5:
        X["is_holiday"] = df.is_holiday.astype(float)
        X["is_weekend"] = df.is_weekend.astype(float)
        X["near_seollal"] = df.seollal_offset.abs().le(3).fillna(False).astype(float)
        X["near_chuseok"] = df.chuseok_offset.abs().le(3).fillna(False).astype(float)
    if row >= 6:
        free = ((df.is_myeongjeol == 1) | (df.is_last_wednesday == 1)).astype(float)
        X["free_rule"] = free
        for s in sites:                                        # 무료 개방 배율을 개소별로
            X[f"free_x_{s}"] = free * (df.site == s).astype(float)
        if with_month:
            for m in range(2, 13):
                X[f"month_{m}"] = (df.month == m).astype(float)
    if row >= 7:
        X["neighbor_closed_n"] = df.neighbor_closed_n.astype(float)
    return X


def fit_predict(hist, tgt, row, sites, with_month=False):
    Xh = feature_block(hist, row, sites, with_month).values
    yh = np.log(hist.total.values)
    beta, *_ = np.linalg.lstsq(Xh, yh, rcond=None)
    resid = yh - Xh @ beta
    rq = pd.Series(resid, index=hist.index).groupby(hist.site.values).quantile(QUANTILE)
    Xt = feature_block(tgt, row, sites, with_month).values
    q = tgt.site.map(rq).fillna(float(np.quantile(resid, QUANTILE))).values
    return np.exp(Xt @ beta + q)


def _rows(df, with_month):
    """원점별 행 3~7 예측 (와이드 표)."""
    sites = sorted(df.site.unique())
    d = df.copy()
    d["dow"] = d.date.dt.weekday
    out = []
    for origin in ORIGINS:
        end = origin + pd.offsets.MonthBegin(1)
        hist = d[(d.date < origin) & (d.actual_closed == 0) & (d.total > 0)]
        tgt = d[(d.date >= origin) & (d.date < end)].copy()
        if tgt.empty:
            continue
        for row in [3, 4, 5, 6, 7]:
            tgt[f"행{row}"] = fit_predict(hist, tgt, row, sites, with_month)
        out.append(tgt.assign(origin=origin)[["origin", "site", "date"] + [f"행{r}" for r in range(3, 8)]])
    return pd.concat(out, ignore_index=True)


def predict_regression(df):
    """긴 표: 배율 행3 ~ 행7, 배율+월(행6)."""
    plain = _rows(df, with_month=False)
    month = _rows(df, with_month=True)
    plain_long = plain.melt(id_vars=["origin", "site", "date"], var_name="model", value_name="pred")
    plain_long["model"] = "배율 " + plain_long.model
    month_row6 = month[["origin", "site", "date", "행6"]].rename(columns={"행6": "pred"})
    month_row6["model"] = "배율+월 (행6)"
    return pd.concat([plain_long, month_row6], ignore_index=True)
