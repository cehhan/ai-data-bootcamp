"""
궁·능 관람객 학습 데이터 정리 스크립트 (백업용)

원본 파일 4개(관람객·개소·달력·검산값)에서 학습용 기본 테이블
train_2023_2025_core.csv 를 다시 만듭니다.

정리 규칙
- 기간: 2023-01-01 ~ 2025-12-31 (궁·종묘·왕릉 3개 유형이 같은 기간)
- 관람객 값은 원본 그대로 (고치거나 채우지 않음)
- 휴관 기준: actual_closed = (total == 0)
    -> 학습 행 선택과 평가 제외에만 사용, 모형 피처로는 쓰지 않음
- 미래 정보 누수 열(paid, free, domestic, foreign_*)은 남기지 않음
- 피처는 근무표 확정 시점에 미리 알 수 있는 달력 정보만 남김

사용법
    python build_train_core.py --data_dir ./data --out train_2023_2025_core.csv
"""

# ---------------------------------------------------------------------------
# 0. 라이브러리
# ---------------------------------------------------------------------------
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. 설정
# ---------------------------------------------------------------------------
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"

VISITS_FILE = "heritage_visitors_daily.parquet"
SITES_FILE = "sites.csv"
CALENDAR_FILE = "calendar_kr_2015_2025.csv"
ANCHORS_FILE = "anchors.json"
WEATHER_FILE = "weather_daily.parquet"  # 검산용으로만 읽음

FOREIGN_COLS = ["foreign_en", "foreign_ja", "foreign_zh", "foreign_etc"]

# 왕릉 관리소 (가이드 「예측 단위」 표 기준). 궁·종묘는 개소 이름을 그대로 씀
TOMB_OFFICE = {
    "동구릉": "동부지구", "광릉": "동부지구", "홍유릉": "동부지구", "사릉": "동부지구",
    "태릉": "중부지구", "정릉": "중부지구", "헌릉": "중부지구", "선릉": "중부지구",
    "의릉": "중부지구", "영휘원": "중부지구",
    "서오릉": "서부지구", "서삼릉": "서부지구", "융릉": "서부지구", "파주삼릉": "서부지구",
    "파주장릉": "서부지구", "김포장릉": "서부지구", "양주온릉": "서부지구",
    "세종대왕유적": "세종대왕유적",
}

# 최종 열 순서
CORE_COLS = [
    # 키
    "date", "site", "group", "office",
    # 정답
    "total",
    # 필터 (피처 아님)
    "actual_closed",
    # 달력 피처
    "dow", "month", "is_weekend", "is_holiday", "is_regular_closed_wd",
    "is_myeongjeol", "myeongjeol_len", "seollal_offset", "chuseok_offset",
    "is_last_wednesday",
]

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]  # pandas dayofweek 0=월


# ---------------------------------------------------------------------------
# 2. 원본 읽기
# ---------------------------------------------------------------------------
def load_raw(data_dir: Path):
    visits = pd.read_parquet(data_dir / VISITS_FILE)
    sites = pd.read_csv(data_dir / SITES_FILE)
    calendar = pd.read_csv(data_dir / CALENDAR_FILE, parse_dates=["date"])
    with open(data_dir / ANCHORS_FILE, encoding="utf-8") as f:
        anchors = json.load(f)
    weather_path = data_dir / WEATHER_FILE
    weather = pd.read_parquet(weather_path) if weather_path.exists() else None
    return visits, sites, calendar, anchors, weather


# ---------------------------------------------------------------------------
# 3. 검산값 7개 확인 (하나라도 다르면 중단)
# ---------------------------------------------------------------------------
def check_anchors(visits, calendar, anchors, weather):
    checks = [
        ("관람객 표 행 수", len(visits), anchors["rows"]),
        ("개소 수", visits["site"].nunique(), anchors["n_sites"]),
        ("total 합", int(visits["total"].sum()), anchors["sums"]["total"]),
        ("외국인 4열 합", int(visits[FOREIGN_COLS].sum().sum()), anchors["sums"]["foreign_all"]),
        ("total 이 0 인 행", int((visits["total"] == 0).sum()), anchors["zero_total_site_days"]["all"]),
        ("달력 행 수", len(calendar), anchors["calendar"]["rows"]),
    ]
    if weather is not None:
        checks.append(("날씨 표 행 수", len(weather), anchors["weather"]["rows"]))

    print("[검산값]")
    ok = True
    for name, got, expected in checks:
        flag = "OK" if got == expected else "MISMATCH"
        ok &= got == expected
        print(f"  {name:<14} {got:>13,} / {expected:>13,}  {flag}")
    if weather is None:
        print("  날씨 표 행 수   (weather_daily.parquet 없음: 건너뜀)")
    if not ok:
        raise ValueError("검산값이 맞지 않습니다. 파일을 다시 받으세요.")


# ---------------------------------------------------------------------------
# 4. 달력 피처: 명절 연휴 블록
#    설날·추석 당일이 포함된, 주말·공휴일이 이어진 구간 전체를 명절 연휴로 봄
# ---------------------------------------------------------------------------
def add_myeongjeol(calendar: pd.DataFrame) -> pd.DataFrame:
    cal = calendar.sort_values("date").reset_index(drop=True).copy()
    names = cal["holiday_name"].fillna("")

    # 쉬는 날 = 주말 또는 공휴일
    cal["is_offday"] = (cal["is_holiday"] == 1) | cal["weekday"].isin(["토", "일"])

    # 쉬는 날이 이어지는 구간마다 번호를 붙임
    cal["off_block"] = (cal["is_offday"] != cal["is_offday"].shift()).cumsum()

    # 설날·추석 공휴일이 하나라도 들어 있는 쉬는 날 구간 = 명절 연휴
    is_mj_holiday = names.str.contains("설날|추석") & cal["is_offday"]
    mj_blocks = set(cal.loc[is_mj_holiday, "off_block"])
    cal["is_myeongjeol"] = (cal["is_offday"] & cal["off_block"].isin(mj_blocks)).astype(int)

    # 연휴 길이: 명절 연휴 날에는 그 구간의 날 수, 아니면 0
    block_len = cal.groupby("off_block")["date"].transform("size")
    cal["myeongjeol_len"] = np.where(cal["is_myeongjeol"] == 1, block_len, 0).astype(int)

    return cal.drop(columns=["off_block"])


# ---------------------------------------------------------------------------
# 5. 학습 테이블 만들기
# ---------------------------------------------------------------------------
def build_core(visits, sites, calendar) -> pd.DataFrame:
    # 5-1. 기간 자르기
    v = visits[(visits["date"] >= START_DATE) & (visits["date"] <= END_DATE)].copy()

    # 5-2. 키 중복 확인
    dup = v.duplicated(["date", "site"]).sum()
    assert dup == 0, f"(date, site) 중복 {dup}행"

    # 5-3. 관리소
    v["office"] = np.where(v["group"] == "왕릉", v["site"].map(TOMB_OFFICE), v["site"])
    assert v["office"].notna().all(), "관리소가 비어 있는 개소가 있습니다"

    # 5-4. 실제 휴관 = 관람객 0 (휴관일은 행이 있고 값이 0)
    v["actual_closed"] = (v["total"] == 0).astype(int)

    # 5-5. 달력 결합
    cal = add_myeongjeol(calendar)
    cal_cols = ["date", "weekday", "is_holiday", "is_last_wednesday",
                "seollal_offset", "chuseok_offset", "is_myeongjeol", "myeongjeol_len"]
    v = v.merge(cal[cal_cols], on="date", how="left", validate="many_to_one")
    assert v["weekday"].notna().all(), "달력에 없는 날짜가 있습니다"

    # 5-6. 요일·월·주말
    v["dow"] = v["date"].dt.dayofweek          # 0=월 ... 6=일
    v["month"] = v["date"].dt.month
    v["is_weekend"] = (v["dow"] >= 5).astype(int)

    # 5-7. 정기 휴관 요일 여부 (sites.csv 의 closed_weekday 와 비교)
    v = v.merge(sites[["site", "closed_weekday"]], on="site", how="left", validate="many_to_one")
    v["is_regular_closed_wd"] = (v["weekday"] == v["closed_weekday"]).astype(int)

    # 5-8. 형 정리
    int_cols = ["total", "actual_closed", "is_holiday", "is_last_wednesday",
                "is_myeongjeol", "myeongjeol_len"]
    v[int_cols] = v[int_cols].astype(int)

    core = v[CORE_COLS].sort_values(["site", "date"]).reset_index(drop=True)
    return core


# ---------------------------------------------------------------------------
# 6. 결과 점검
# ---------------------------------------------------------------------------
def check_core(core: pd.DataFrame, visits: pd.DataFrame):
    v = visits[(visits["date"] >= START_DATE) & (visits["date"] <= END_DATE)]
    n_days = (pd.Timestamp(END_DATE) - pd.Timestamp(START_DATE)).days + 1

    assert len(core) == len(v), "행 수가 원본 기간과 다릅니다"
    assert len(core) == n_days * core["site"].nunique(), "빠진 날짜가 있습니다"
    assert core["total"].sum() == v["total"].sum(), "total 합이 원본과 다릅니다"
    assert (core["actual_closed"] == (core["total"] == 0)).all()
    assert core.drop(columns=["seollal_offset", "chuseok_offset"]).notna().all().all(), \
        "명절 offset 외 열에 빈 값이 있습니다"

    print("\n[결과]")
    print(f"  행 {len(core):,} · 열 {core.shape[1]} · 개소 {core['site'].nunique()}")
    print(f"  기간 {core['date'].min().date()} ~ {core['date'].max().date()}")
    print(f"  total 합 {core['total'].sum():,}")
    print(f"  휴관(actual_closed=1) {core['actual_closed'].sum():,}행 / 학습 가능 {(core['actual_closed'] == 0).sum():,}행")
    print(f"  명절 연휴 {core.loc[core['is_myeongjeol'] == 1, 'date'].nunique()}일 · "
          f"마지막 수요일 {core.loc[core['is_last_wednesday'] == 1, 'date'].nunique()}일")


# ---------------------------------------------------------------------------
# 7. 실행
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=".", help="원본 파일이 있는 폴더")
    parser.add_argument("--out", default="train_2023_2025_core.csv", help="저장할 CSV 경로")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    visits, sites, calendar, anchors, weather = load_raw(data_dir)

    check_anchors(visits, calendar, anchors, weather)
    core = build_core(visits, sites, calendar)
    check_core(core, visits)

    # 엑셀에서 한글이 깨지지 않도록 utf-8-sig
    core.to_csv(args.out, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
