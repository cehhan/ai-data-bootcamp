"""무료 개방 효과 크기 (개소별 배율).

    python scripts/free_day_effect.py

2023~2025년 개방일에서 개소별로
    배율 = 무료 개방일 평균 관람객 ÷ 같은 요일 일반 개방일 평균 관람객
을 계산합니다. 무료 개방일은 두 종류로 나눕니다.
 - 마지막 수요일 : is_last_wednesday == 1 이고 공휴일·명절이 아닌 날 (모두 수요일)
 - 명절 연휴     : is_myeongjeol == 1 (설·추석이 든 연휴 블록, 요일이 섞임)
일반 개방일 = 실제로 문을 열었고(actual_closed == 0, total > 0) 공휴일·명절·마지막 수요일·예정 휴관이 아닌 날.
'같은 요일' 은 무료 개방일 하나하나의 요일에 맞춰 그 개소의 같은 요일 일반 개방일 평균을 기준으로 씁니다
(명절 연휴처럼 요일이 섞인 경우 날마다 기준을 맞춘 뒤 합산).

이 표는 설명용(보고서 6-1)입니다. 예측·보정 규칙에서 쓰는 배율은 누수를 막기 위해
forecast_fva.horizon_models.free_day_multipliers 로 원점 전날까지의 기록만 써서 따로 계산합니다.

결과: results/무료개방_효과_개소별.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from forecast_fva.data import load_train  # noqa: E402

RESULTS = ROOT / "results"


def effect(df, free_mask, name):
    op = df[(df.actual_closed == 0) & (df.total > 0)].copy()
    op["dow"] = op.date.dt.weekday
    normal = op[(op.is_holiday == 0) & (op.is_myeongjeol == 0) & (op.is_last_wednesday == 0)
                & (op.planned_closed == 0)]
    base = normal.groupby(["site", "dow"]).total.mean().rename("base")
    free = op[free_mask(op)].join(base, on=["site", "dow"])
    g = free.groupby(["site", "group"]).agg(n=("total", "size"), free_mean=("total", "mean"),
                                            base_mean=("base", "mean"))
    g["ratio"] = free.groupby(["site", "group"]).total.sum() / free.groupby(["site", "group"]).base.sum()
    g.columns = pd.MultiIndex.from_product([[name], ["무료일 수", "무료일 평균", "같은 요일 일반일 평균", "배율"]])
    return g


def main():
    df = load_train()
    lw = effect(df, lambda d: (d.is_last_wednesday == 1) & (d.is_holiday == 0) & (d.is_myeongjeol == 0),
                "마지막 수요일")
    mj = effect(df, lambda d: d.is_myeongjeol == 1, "명절 연휴")
    t = lw.join(mj, how="outer")
    t.columns = [f"{a} {b}" for a, b in t.columns]
    t = t.reset_index().rename(columns={"site": "개소", "group": "구분"})
    t = t.sort_values(["구분", "마지막 수요일 배율"], ascending=[True, False])
    num = [c for c in t.columns if c not in ("개소", "구분")]
    t[num] = t[num].round(2)

    # 구분별 요약 (개소 배율의 중앙값)
    summ = t.groupby("구분")[["마지막 수요일 배율", "명절 연휴 배율"]].median().round(2)

    RESULTS.mkdir(exist_ok=True)
    t.to_csv(RESULTS / "무료개방_효과_개소별.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 200)
    print(t.to_string(index=False))
    print("\n구분별 중앙값\n" + summ.to_string())
    print(f"\n저장: {RESULTS / '무료개방_효과_개소별.csv'}")


if __name__ == "__main__":
    main()
