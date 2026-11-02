"""
FVA 1차 (요구사항 6): 정보를 하나씩 더할 때의 비용 변화
7일 예측, 목요일 원점 26개 (2025-07-03 ~ 2025-12-25), 평가 행 = 실제 개방일

행
1. 직전 7일 평균 (운영팀 현재 방식)
2. + 서비스 수준 보정 (개소별, 직전 8개 원점의 실제/ma7 0.8 분위수)
3. LightGBM q0.8 : 과거 관람객 피처 + 개소·요일·월·정기 휴관 요일
4. + 공휴일·명절 연휴 (is_holiday, is_myeongjeol, myeongjeol_len, 설·추석 offset)
5. + 마지막 수요일 (is_last_wednesday)

공통 설정
- 정답 = total / level_med28_norm (원점 전 최근 28개 평소 개방일 중앙값)
- 학습 행 = 정답 날짜 < 원점, 개방일 / 손실 = 분위수(alpha 0.8) / 시드 42
"""

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

FEATURES_FILE = "origin_features_h31.csv"
CORE_FILE = "train_2023_2025_core.csv"
H = 7
BT_ORIGINS = pd.date_range("2025-07-03", "2025-12-25", freq="7D")
TAU, CU, CO, PER, SEED = 0.8, 600_000, 150_000, 2000, 42

PAST = ["horizon", "r_last", "r_ma7", "r_snaive", "r_dow4", "r_mean14", "r_mean28", "log_level"]
BASIC = ["site_c", "group_c", "dow", "is_weekend", "month", "is_regular_closed_wd"]
HOLIDAY = ["is_holiday", "is_myeongjeol", "myeongjeol_len", "seollal_offset", "chuseok_offset"]
LASTWED = ["is_last_wednesday"]
ROWS = {
    "3. 모형: 과거 관람객 + 개소·요일·월": PAST + BASIC,
    "4. + 공휴일·명절 연휴": PAST + BASIC + HOLIDAY,
    "5. + 마지막 수요일": PAST + BASIC + HOLIDAY + LASTWED,
}

df = pd.read_csv(FEATURES_FILE, parse_dates=["origin", "date"])
df = df[(df["horizon"] <= H) & (df["is_forecast"] == 0)].copy()
df["level"] = df["level_med28_norm"].clip(lower=1)
for c, src in [("r_last", "last_open"), ("r_ma7", "ma7_open"), ("r_snaive", "snaive7"),
               ("r_dow4", "dow_mean4"), ("r_mean14", "level_mean14"), ("r_mean28", "level_mean28")]:
    df[c] = df[src] / df["level"]
df["log_level"] = np.log1p(df["level"])
df["site_c"] = pd.Categorical(df["site"], categories=sorted(df["site"].unique()))
df["group_c"] = pd.Categorical(df["group"], categories=sorted(df["group"].unique()))
df["event"] = np.select([df["is_myeongjeol"] == 1, df["is_last_wednesday"] == 1, df["is_holiday"] == 1],
                        ["명절 연휴", "마지막 수요일", "공휴일"], default="평소")


def cost(y, q):
    n, p = y / PER, q / PER
    return CU * np.clip(n - p, 0, None) + CO * np.clip(p - n, 0, None)


def lgbm_predict(train, test, feats):
    m = lgb.LGBMRegressor(objective="quantile", alpha=TAU, n_estimators=400, learning_rate=0.05,
                          num_leaves=31, min_child_samples=40, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.8, random_state=SEED, verbose=-1)
    m.fit(train[feats], train["total"] / train["level"])
    return np.clip(m.predict(test[feats]), 0, None) * test["level"].to_numpy()


preds = []
for O in BT_ORIGINS:
    test = df[df["origin"] == O].copy()
    hist = df[(df["date"] < O) & (df["actual_closed"] == 0)]
    test["1. 직전 7일 평균"] = test["ma7_open"]
    prev = hist[hist["origin"].between(O - pd.Timedelta(days=56), O - pd.Timedelta(days=7))]
    f = (prev["total"] / prev["ma7_open"]).groupby(prev["site"]).quantile(TAU)
    test["2. + 서비스 수준 보정"] = test["ma7_open"] * test["site"].map(f).fillna(1.0)
    for name, feats in ROWS.items():
        test[name] = lgbm_predict(hist, test, feats)
    preds.append(test)
res = pd.concat(preds, ignore_index=True)
ev = res[res["actual_closed"] == 0].copy()
NAMES = ["1. 직전 7일 평균", "2. + 서비스 수준 보정"] + list(ROWS)

# MASE / sPL 척도: 학습 기간 개방일의 7일 전 값 대비 오차 평균 (개소별)
core = pd.read_csv(CORE_FILE, parse_dates=["date"])
tr = core[core["date"] < BT_ORIGINS[0]].copy()
tr.loc[tr["actual_closed"] == 1, "total"] = np.nan
tr = tr.sort_values(["site", "date"])
scale = (tr["total"] - tr.groupby("site")["total"].shift(7)).abs().groupby(tr["site"]).mean()

rows = []
for n in NAMES:
    c = cost(ev["total"], ev[n])
    rows.append({"행": n, "비용(원)": c.sum(), "적중률(%)": (ev["total"] <= ev[n]).mean() * 100,
                 "MASE": ((ev[n] - ev["total"]).abs().groupby(ev["site"]).mean() / scale).mean()})
fva = pd.DataFrame(rows)
fva["앞 행보다 줄어든 비용(원)"] = (-fva["비용(원)"].diff()).fillna(0)
fva["직전 7일 평균 대비 절감(원)"] = fva["비용(원)"].iloc[0] - fva["비용(원)"]

pd.set_option("display.width", 200)
fmt = fva.copy()
for c in ["비용(원)", "앞 행보다 줄어든 비용(원)", "직전 7일 평균 대비 절감(원)"]:
    fmt[c] = fmt[c].map(lambda x: f"{x:,.0f}")
fmt["적중률(%)"] = fmt["적중률(%)"].round(1)
fmt["MASE"] = fmt["MASE"].round(3)
print(f"평가 행 {len(ev):,}\n")
print("[FVA]"); print(fmt.to_string(index=False))

print("\n[날짜 유형별 비용 (억 원)]")
print(pd.DataFrame({n: cost(ev["total"], ev[n]).groupby(ev["event"]).sum() / 1e8 for n in NAMES}).round(2).T)

print("\n[원점별 비용 (백만 원): 직전 7일 평균 vs 최종 행]")
per = pd.DataFrame({n: cost(ev["total"], ev[n]).groupby(ev["origin"]).sum() / 1e6 for n in [NAMES[0], NAMES[1], NAMES[-1]]})
per.index = per.index.strftime("%m-%d")
print(per.round(1).T.to_string())

fva.to_csv("fva_v1.csv", index=False, encoding="utf-8-sig")
res.to_csv("fva_v1_predictions.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
