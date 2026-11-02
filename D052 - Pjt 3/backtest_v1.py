"""
1차 백테스트: 베이스라인 3개 + 서비스 수준 보정 + 후보 모형 2개 (7일 예측, 목요일 원점 26개)

평가 규칙
- 원점 O 의 예측에는 O 전날까지의 데이터만 씀 (학습 행도 정답 날짜가 O 전날 이하인 것만)
- 평가 행 = 실제 actual_closed == 0 인 행
- 비용(원) = 600,000 x max(n - q, 0) + 150,000 x max(q - n, 0),  n = 실제/2000, q = 예측/2000 (올림 없음)
- 적중률 = 실제 <= 예측 인 비율 (0.8 분위수면 80% 근처가 목표)

후보
- naive      : 마지막 개방일 값
- snaive7    : 가장 최근 같은 요일 개방일 값
- ma7        : 직전 7일 개방일 평균 (운영팀 현재 방식)
- ma7_sl     : ma7 x 개소별 보정계수 (직전 8개 원점의 "실제/ma7" 0.8 분위수)   -> FVA 2행
- rule_q80   : 배수 규칙 모형. 평소 수준 x (개소·요일별 0.8 분위 배수), 공휴일·명절·마지막 수요일은 유형별 배수
- lgbm_q80   : LightGBM 분위수(0.8) 글로벌 모형. 정답 = total / 평소 수준
"""

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

FEATURES_FILE = "origin_features_h31.csv"
H = 7
BT_ORIGINS = pd.date_range("2025-07-03", "2025-12-25", freq="7D")  # 26개
TAU = 0.8
CU, CO, PER = 600_000, 150_000, 2000
SEED = 42

df = pd.read_csv(FEATURES_FILE, parse_dates=["origin", "date"])
df = df[(df["horizon"] <= H) & (df["is_forecast"] == 0)].copy()
df["level"] = df["level_med28_norm"].clip(lower=1)
df["event"] = np.select(
    [df["is_myeongjeol"] == 1, df["is_last_wednesday"] == 1, df["is_holiday"] == 1],
    ["myeongjeol", "last_wed", "holiday"], default="normal")


def cost(y, q):
    n, p = y / PER, q / PER
    return CU * np.clip(n - p, 0, None) + CO * np.clip(p - n, 0, None)


# ---------------------------------------------------------------------------
# 후보별 예측
# ---------------------------------------------------------------------------
def predict_origin(O: pd.Timestamp) -> pd.DataFrame:
    test = df[df["origin"] == O].copy()
    # 학습에 쓸 수 있는 행: 정답 날짜가 원점 전날 이하, 개방일
    hist = df[(df["date"] < O) & (df["actual_closed"] == 0)]

    # 베이스라인
    test["naive"] = test["last_open"]
    test["snaive7"] = test["snaive7"]
    test["ma7"] = test["ma7_open"]

    # 서비스 수준 보정: 직전 8개 원점(정답이 모두 O 전날 이하)의 실제/ma7 비율 0.8 분위수, 개소별
    prev = hist[hist["origin"].between(O - pd.Timedelta(days=56), O - pd.Timedelta(days=7))]
    f = (prev["total"] / prev["ma7_open"]).groupby(prev["site"]).quantile(TAU)
    test["ma7_sl"] = test["ma7_open"] * test["site"].map(f).fillna(1.0)

    # 배수 규칙 모형 (최근 1년 학습 행)
    h1 = hist[hist["date"] >= O - pd.Timedelta(days=365)]
    r = h1["total"] / h1["level"]
    normal = h1["event"] == "normal"
    m_dow = r[normal].groupby([h1.loc[normal, "site"], h1.loc[normal, "dow"]]).quantile(TAU)
    m_evt = r[~normal].groupby([h1.loc[~normal, "group"], h1.loc[~normal, "event"]]).quantile(TAU)
    key_dow = pd.MultiIndex.from_frame(test[["site", "dow"]])
    key_evt = pd.MultiIndex.from_frame(test[["group", "event"]])
    mult = np.where(test["event"] == "normal",
                    m_dow.reindex(key_dow).to_numpy(),
                    m_evt.reindex(key_evt).to_numpy())
    mult = pd.Series(mult, index=test.index).fillna(m_dow.reindex(key_dow).set_axis(test.index))
    test["rule_q80"] = test["level"] * mult.fillna(1.0)

    # LightGBM 분위수 글로벌 모형
    feats = ["horizon", "dow", "month", "is_weekend", "is_holiday", "is_regular_closed_wd",
             "is_myeongjeol", "myeongjeol_len", "seollal_offset", "chuseok_offset",
             "is_last_wednesday", "site_c", "group_c",
             "r_last", "r_ma7", "r_snaive", "r_dow4", "r_mean14", "r_mean28", "log_level"]

    def make_x(d):
        x = pd.DataFrame(index=d.index)
        for c in feats[:11]:
            x[c] = d[c]
        x["site_c"] = d["site"].astype("category")
        x["group_c"] = d["group"].astype("category")
        for c, src in [("r_last", "last_open"), ("r_ma7", "ma7_open"), ("r_snaive", "snaive7"),
                       ("r_dow4", "dow_mean4"), ("r_mean14", "level_mean14"), ("r_mean28", "level_mean28")]:
            x[c] = d[src] / d["level"]
        x["log_level"] = np.log1p(d["level"])
        return x

    cats = sorted(df["site"].unique()), sorted(df["group"].unique())
    xtr, xte = make_x(hist), make_x(test)
    for x in (xtr, xte):
        x["site_c"] = pd.Categorical(x["site_c"].astype(str), categories=cats[0])
        x["group_c"] = pd.Categorical(x["group_c"].astype(str), categories=cats[1])
    model = lgb.LGBMRegressor(objective="quantile", alpha=TAU, n_estimators=400, learning_rate=0.05,
                              num_leaves=31, min_child_samples=40, subsample=0.8, subsample_freq=1,
                              colsample_bytree=0.8, random_state=SEED, verbose=-1)
    model.fit(xtr, hist["total"] / hist["level"])
    test["lgbm_q80"] = np.clip(model.predict(xte), 0, None) * test["level"]
    return test


MODELS = ["naive", "snaive7", "ma7", "ma7_sl", "rule_q80", "lgbm_q80"]
res = pd.concat([predict_origin(O) for O in BT_ORIGINS], ignore_index=True)
ev = res[res["actual_closed"] == 0].copy()
for m in MODELS:
    ev[f"cost_{m}"] = cost(ev["total"], ev[m])
    ev[f"hit_{m}"] = ev["total"] <= ev[m]

# ---------------------------------------------------------------------------
# 요약
# ---------------------------------------------------------------------------
def summary(d):
    out = {}
    for m in MODELS:
        out[m] = {"비용(억원)": d[f"cost_{m}"].sum() / 1e8,
                  "적중률(%)": d[f"hit_{m}"].mean() * 100,
                  "WAPE(%)": (d["total"] - d[m]).abs().sum() / d["total"].sum() * 100}
    return pd.DataFrame(out).T.round(2)

print(f"평가 행 {len(ev):,} (원점 {res['origin'].nunique()}개 x 23개소 x 7일 중 개방일)\n")
print("[전체]"); print(summary(ev))
print("\n[날짜 유형별 비용(억원)]")
print(ev.groupby("event")[[f"cost_{m}" for m in MODELS]].sum().div(1e8).round(2)
      .rename(columns=lambda c: c[5:]))
print("\n[개소 유형별 비용(억원)]")
print(ev.groupby("group")[[f"cost_{m}" for m in MODELS]].sum().div(1e8).round(2)
      .rename(columns=lambda c: c[5:]))
wins = (ev.groupby("origin")[[f"cost_{m}" for m in MODELS]].sum()
          .apply(lambda r: r < r["cost_ma7"], axis=1).sum())
print("\n[원점 26개 중 직전 7일 평균보다 비용이 낮았던 원점 수]")
print(wins.rename(lambda c: c[5:]).drop("ma7"))
res.to_csv("backtest_v1_predictions.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
