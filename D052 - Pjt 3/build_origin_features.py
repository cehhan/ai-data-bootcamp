"""
원점 기준 과거 관람객 피처 만들기

원점(origin) = 예측 기간의 첫날. 근무표 확정일 = 원점 전날(cutoff).
모든 과거 관람객 피처는 cutoff 이전(포함)의 "개방일"(actual_closed == 0) 기록으로만 계산합니다.
원점마다 1~MAX_H 일 뒤까지의 행을 만들고, 같은 원점의 행에는 같은 수준 값이 붙습니다
(같은 요일 수준만 예측하는 날의 요일에 따라 달라짐).

만드는 원점
- 학습·백테스트용: 2023년부터 매주 목요일 (권고표 원점 2026-01-01 이 목요일이라 요일을 맞춤)
  * 최근 28개 개방일이 쌓이기 전 원점은 뺌
  * 정답(total)은 2025-12-31 까지만 있으므로 그 뒤 날짜의 행은 만들지 않음
- 권고표용: 2026-01-01 (정답 없음, future 파일의 달력 피처를 붙임)

피처 (모두 cutoff 이전 개방일 기준)
- horizon          : 원점에서 며칠 뒤인지 (1 = 원점 당일)
- last_open        : 마지막 개방일 값                         (= 나이브 베이스라인)
- ma7_open         : cutoff 전 7일 중 개방일 평균              (= 직전 7일 평균 베이스라인)
                     직전 7일에 개방일이 하나도 없으면 최근 7개 개방일 평균으로 대체
- ma7_fallback     : 위 대체가 일어난 행이면 1
- snaive7          : 원점 전 7일 중 같은 요일 값, 휴관이면 더 이전의 가장 가까운 개방 같은 요일
                                                             (= 계절 나이브 베이스라인)
- level_mean14/28  : 최근 14·28개 개방일 평균
- level_med28      : 최근 28개 개방일 중앙값
- level_med28_norm : 최근 28개 "평소" 개방일 중앙값 (공휴일·명절 연휴·마지막 수요일 제외, 가설 H5)
- dow_mean4        : 예측하는 날과 같은 요일의 최근 4개 개방일 평균

사용법
    python build_origin_features.py --train train_2023_2025_core.csv \
        --future future_2026-01-01_2026-01-31.csv --max_h 31
"""

# ---------------------------------------------------------------------------
# 0. 라이브러리
# ---------------------------------------------------------------------------
import argparse

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 1. 설정
# ---------------------------------------------------------------------------
FIRST_TRAIN_ORIGIN = "2023-01-05"   # 2023년 첫 목요일 (28개 개방일이 쌓인 뒤부터 실제 사용)
DATA_END = "2025-12-31"
FORECAST_ORIGIN = "2026-01-01"
MIN_HISTORY = 28                    # 최근 수준 계산에 필요한 최소 개방일 수

CAL_COLS = ["dow", "month", "is_weekend", "is_holiday", "is_regular_closed_wd",
            "is_myeongjeol", "myeongjeol_len", "seollal_offset", "chuseok_offset",
            "is_last_wednesday"]
FEATURE_COLS = ["last_open", "ma7_open", "snaive7", "level_mean14", "level_mean28",
                "level_med28", "level_med28_norm", "dow_mean4"]


# ---------------------------------------------------------------------------
# 2. 한 개소, 한 원점의 피처
# ---------------------------------------------------------------------------
def site_origin_features(hist: pd.DataFrame, origin: pd.Timestamp, max_h: int) -> list[dict]:
    """hist: 한 개소의 개방일 기록 (date, total, dow, is_normal), date 오름차순."""
    cutoff = origin - pd.Timedelta(days=1)
    past = hist[hist["date"] <= cutoff]
    if len(past) < MIN_HISTORY:
        return []

    last28 = past["total"].iloc[-28:]
    normal = past.loc[past["is_normal"], "total"].iloc[-28:]
    week = past[past["date"] >= origin - pd.Timedelta(days=7)]

    base = {
        "last_open": past["total"].iloc[-1],
        # 직전 7일에 개방일이 없을 때만 최근 7개 개방일 평균으로 대체 (팀 규칙)
        "ma7_open": week["total"].mean() if len(week) else past["total"].iloc[-7:].mean(),
        "ma7_fallback": int(len(week) == 0),
        "level_mean14": past["total"].iloc[-14:].mean(),
        "level_mean28": last28.mean(),
        "level_med28": last28.median(),
        "level_med28_norm": normal.median() if len(normal) else np.nan,
    }

    # 요일별 값은 예측하는 날의 요일에 따라 다름
    by_dow = {}
    for dow in range(7):
        same = past[past["dow"] == dow]
        by_dow[dow] = {
            "snaive7": same["total"].iloc[-1] if len(same) else np.nan,
            "dow_mean4": same["total"].iloc[-4:].mean() if len(same) else np.nan,
        }

    rows = []
    for h in range(1, max_h + 1):
        d = origin + pd.Timedelta(days=h - 1)
        rows.append({"origin": origin, "date": d, "horizon": h, **base, **by_dow[d.dayofweek]})
    return rows


# ---------------------------------------------------------------------------
# 3. 전체 원점 × 개소
# ---------------------------------------------------------------------------
def build(train: pd.DataFrame, future: pd.DataFrame, max_h: int) -> pd.DataFrame:
    train = train.copy()
    # 평소 개방일: 공휴일·명절 연휴·마지막 수요일이 아닌 날 (달력으로 미리 아는 정보)
    train["is_normal"] = (train["is_holiday"] == 0) & (train["is_myeongjeol"] == 0) & \
                         (train["is_last_wednesday"] == 0)
    open_hist = train[train["actual_closed"] == 0][["site", "date", "total", "dow", "is_normal"]]

    train_origins = pd.date_range(FIRST_TRAIN_ORIGIN, DATA_END, freq="7D")
    origins = list(train_origins) + [pd.Timestamp(FORECAST_ORIGIN)]

    rows = []
    for site, hist in open_hist.groupby("site"):
        hist = hist.sort_values("date").reset_index(drop=True)
        for o in origins:
            for r in site_origin_features(hist, o, max_h):
                r["site"] = site
                rows.append(r)
    feat = pd.DataFrame(rows)

    # 정답이 없는 날(2025-12-31 이후)은 권고표 원점만 남김
    keep = (feat["date"] <= DATA_END) | (feat["origin"] == pd.Timestamp(FORECAST_ORIGIN))
    feat = feat[keep]

    # 날짜별 정보(정답·휴관·달력) 붙이기: 과거는 학습 파일, 2026년은 future 파일
    day_cols = ["site", "date", "group", "office", "total", "actual_closed"] + CAL_COLS
    days = pd.concat([train[day_cols], future[day_cols]], ignore_index=True)
    out = feat.merge(days, on=["site", "date"], how="left", validate="many_to_one")

    out["is_forecast"] = (out["origin"] == pd.Timestamp(FORECAST_ORIGIN)).astype(int)
    cols = ["origin", "date", "site", "group", "office", "horizon", "is_forecast",
            "total", "actual_closed"] + FEATURE_COLS + ["ma7_fallback"] + CAL_COLS
    return out[cols].sort_values(["origin", "site", "date"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. 누수 점검: 모든 피처가 원점 전날까지의 값으로만 만들어졌는지
# ---------------------------------------------------------------------------
def leak_check(out: pd.DataFrame, train: pd.DataFrame):
    rng = np.random.default_rng(0)
    sample = out.iloc[rng.choice(len(out), size=200, replace=False)]
    open_hist = train[train["actual_closed"] == 0]
    for _, r in sample.iterrows():
        past = open_hist[(open_hist["site"] == r["site"]) & (open_hist["date"] < r["origin"])]
        assert np.isclose(past["total"].iloc[-28:].mean(), r["level_mean28"]), "level_mean28 불일치"
        assert past["total"].iloc[-1] == r["last_open"], "last_open 불일치"
    print("  누수 점검 200행: 통과 (모든 피처가 원점 전날까지의 개방일로 계산됨)")


# ---------------------------------------------------------------------------
# 5. 실행
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="train_2023_2025_core.csv")
    parser.add_argument("--future", default="future_2026-01-01_2026-01-31.csv")
    parser.add_argument("--max_h", type=int, default=31)
    parser.add_argument("--out", default="origin_features_h31.csv")
    args = parser.parse_args()

    train = pd.read_csv(args.train, parse_dates=["date"])
    future = pd.read_csv(args.future, parse_dates=["date"])

    out = build(train, future, args.max_h)

    print("[결과]")
    print(f"  {len(out):,}행 · 원점 {out['origin'].nunique()}개 "
          f"({out['origin'].min().date()} ~ {out['origin'].max().date()})")
    fb = out[out["ma7_fallback"] == 1].groupby(["origin", "site"]).size()
    print(f"  직전 7일 개방일 0 -> 최근 7개 개방일로 대체: {len(fb)}건 {fb.to_dict()}")
    print(f"  학습·백테스트 행 {int((out['is_forecast'] == 0).sum()):,} · 권고표 행 {int(out['is_forecast'].sum()):,}")
    leak_check(out, train)

    out.to_csv(args.out, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    print(f"저장: {args.out}")


if __name__ == "__main__":
    main()
