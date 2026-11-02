"""
권고표 예측용 행 만들기 (기본 2026-01-01 ~ 2026-01-31)

- 달력 파일(calendar_kr_2015_2025.csv)이 2025-12-31 까지라서,
  가이드 지정대로 holidays 패키지 0.103 의 holidays.KR 로 2026년 달력을 만듭니다.
- 같은 함수로 2015~2025년 달력을 다시 만들어 원본 달력과 같은지 먼저 확인합니다.
- 결과 열은 학습 파일(train_2023_2025_core.csv)과 같은 16개입니다.
  total, actual_closed 는 미래라서 빈 값입니다.

출력
- calendar_kr_2026.csv              : 2026년 전체 달력 (원본 달력과 같은 열)
- future_2026-01-01_<end>.csv       : 23개소 x 예측 일수 (1월 전체면 713행)

사용법
    pip install holidays==0.103
    python build_future_2026.py --data_dir ./data                    # 1/1~1/31
    python build_future_2026.py --data_dir ./data --end 2026-01-07   # 첫 주만
"""

# ---------------------------------------------------------------------------
# 0. 라이브러리
# ---------------------------------------------------------------------------
import argparse
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

# 학습 파일 스크립트와 같은 규칙을 씁니다 (같은 폴더에 둘 것)
from build_train_core import CORE_COLS, TOMB_OFFICE, add_myeongjeol

# ---------------------------------------------------------------------------
# 1. 설정
# ---------------------------------------------------------------------------
HOLIDAYS_VERSION = "0.103"
FUTURE_START = "2026-01-01"
FUTURE_END = "2026-01-31"
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
OFFSET_WINDOW = 15  # 원본 달력: 설·추석 당일 ±15일 밖은 빈칸


# ---------------------------------------------------------------------------
# 2. 달력 만들기 (원본 달력과 같은 열)
#    앞뒤 해까지 넉넉히 만들어야 명절 연휴 블록과 offset 이 해 경계에서 끊기지 않음
# ---------------------------------------------------------------------------
def make_calendar(start: str, end: str) -> pd.DataFrame:
    assert holidays.__version__ == HOLIDAYS_VERSION, \
        f"holidays {HOLIDAYS_VERSION} 이 필요합니다 (현재 {holidays.__version__})"

    dates = pd.date_range(start, end, freq="D")
    years = range(dates.min().year - 1, dates.max().year + 2)
    kr = holidays.KR(years=years, language="ko")

    cal = pd.DataFrame({"date": dates})
    cal["weekday"] = [WEEKDAY_KR[d.dayofweek] for d in cal["date"]]
    cal["holiday_name"] = [kr.get(d.date()) for d in cal["date"]]
    # 두 공휴일이 겹치면 원본처럼 「;」로 이어짐
    cal["holiday_name"] = cal["holiday_name"].map(lambda s: s.replace(", ", ";") if isinstance(s, str) else s)
    cal["is_holiday"] = cal["holiday_name"].notna().astype(int)

    # 설날·추석 당일 = 공휴일 이름이 정확히 「설날」·「추석」인 날 (원본 README 규칙)
    def day_list(name):
        return sorted(pd.Timestamp(d) for d, n in kr.items() if name in n.split("; ") or n == name
                      or name in [x.strip() for x in n.split(";")])

    def nearest_offset(d, days):
        diffs = [(d - x).days for x in days]
        best = min(diffs, key=abs)
        return best if abs(best) <= OFFSET_WINDOW else np.nan

    seollal = day_list("설날")
    chuseok = day_list("추석")
    cal["seollal_offset"] = [nearest_offset(d, seollal) for d in cal["date"]]
    cal["chuseok_offset"] = [nearest_offset(d, chuseok) for d in cal["date"]]

    # 매월 마지막 수요일
    is_wed = cal["date"].dt.dayofweek == 2
    last_wed = cal[is_wed].groupby(cal["date"].dt.to_period("M"))["date"].transform("max")
    cal["is_last_wednesday"] = 0
    cal.loc[last_wed.index, "is_last_wednesday"] = (cal.loc[last_wed.index, "date"] == last_wed).astype(int)
    return cal


# ---------------------------------------------------------------------------
# 3. 원본 달력과 비교 (같은 방식으로 만들었는지 확인)
# ---------------------------------------------------------------------------
def validate_against_original(orig: pd.DataFrame):
    mine = make_calendar("2014-01-01", "2026-12-31")
    mine = mine[mine["date"].between(orig["date"].min(), orig["date"].max())].reset_index(drop=True)
    o = orig.sort_values("date").reset_index(drop=True)

    print("[원본 달력과 비교: 2015~2025]")
    ok = True
    for col in ["weekday", "is_holiday", "is_last_wednesday", "seollal_offset", "chuseok_offset"]:
        a, b = mine[col], o[col]
        diff = int((~((a == b) | (a.isna() & b.isna()))).sum())
        ok &= diff == 0
        print(f"  {col:<18} 다른 날 {diff}")
    if not ok:
        raise ValueError("원본 달력과 다릅니다. holidays 버전을 확인하세요.")


# ---------------------------------------------------------------------------
# 4. 예측용 행 만들기
# ---------------------------------------------------------------------------
def build_future(sites: pd.DataFrame, cal_all: pd.DataFrame, end: str = FUTURE_END) -> pd.DataFrame:
    cal = add_myeongjeol(cal_all)  # 학습 파일과 같은 명절 연휴 규칙
    cal = cal[cal["date"].between(FUTURE_START, end)]

    grid = sites[["site", "group", "closed_weekday"]].merge(cal, how="cross")
    grid["office"] = np.where(grid["group"] == "왕릉", grid["site"].map(TOMB_OFFICE), grid["site"])

    grid["total"] = np.nan          # 미래: 모름
    grid["actual_closed"] = np.nan  # 미래: 모름
    grid["dow"] = grid["date"].dt.dayofweek
    grid["month"] = grid["date"].dt.month
    grid["is_weekend"] = (grid["dow"] >= 5).astype(int)
    grid["is_regular_closed_wd"] = (grid["weekday"] == grid["closed_weekday"]).astype(int)

    future = grid[CORE_COLS].sort_values(["site", "date"]).reset_index(drop=True)
    n_days = (pd.Timestamp(end) - pd.Timestamp(FUTURE_START)).days + 1
    assert len(future) == 23 * n_days, f"행 수 {len(future)} ({23 * n_days} 이어야 함)"
    # 원점(2026-01-01)에서 며칠 뒤인지: 1 = 첫날
    future.insert(future.columns.get_loc("total"), "horizon", (future["date"] - pd.Timestamp(FUTURE_START)).dt.days + 1)
    return future


# ---------------------------------------------------------------------------
# 5. 실행
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=".")
    parser.add_argument("--out_dir", default=".")
    parser.add_argument("--end", default=FUTURE_END, help="예측 마지막 날 (기본 2026-01-31)")
    args = parser.parse_args()
    data_dir, out_dir = Path(args.data_dir), Path(args.out_dir)

    sites = pd.read_csv(data_dir / "sites.csv")
    orig_cal = pd.read_csv(data_dir / "calendar_kr_2015_2025.csv", parse_dates=["date"])

    validate_against_original(orig_cal)

    # 2025년 말~2027년 초까지 만들어 명절 블록이 해 경계에서 잘리지 않게 함
    cal_all = make_calendar("2025-01-01", "2027-12-31")
    cal_2026 = cal_all[cal_all["date"].dt.year == 2026][orig_cal.columns]
    cal_2026.to_csv(out_dir / "calendar_kr_2026.csv", index=False, encoding="utf-8-sig",
                    date_format="%Y-%m-%d")

    future = build_future(sites, cal_all, args.end)
    out = out_dir / f"future_{FUTURE_START}_{args.end}.csv"
    future.to_csv(out, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    print("\n[2026 달력]")
    print(f"  공휴일 {int(cal_2026['is_holiday'].sum())}일")
    print(cal_2026.loc[cal_2026["is_holiday"] == 1, ["date", "weekday", "holiday_name"]]
          .to_string(index=False))
    print("\n[예측용 행]")
    print(f"  {len(future)}행 · 기간 {FUTURE_START} ~ {args.end}")
    print(future.drop_duplicates("date")[["date", "dow", "is_holiday", "is_myeongjeol",
                                          "is_last_wednesday"]].to_string(index=False))
    closed = future[future["is_regular_closed_wd"] == 1].groupby("date")["site"].apply(list)
    print("\n  정기 휴관 요일에 해당하는 개소")
    for d, s in closed.items():
        print(f"    {d.date()}: {len(s)}곳 ({', '.join(s)})")
    print(f"\n저장: {out}, {out_dir / 'calendar_kr_2026.csv'}")


if __name__ == "__main__":
    main()
