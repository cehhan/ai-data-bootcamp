# 보고서 도표 fig01~fig10 생성 (report_v8에 들어간 그림과 같은 코드)
# 각 그림의 제목은 발견 문장, 아래에 단위·출처 줄을 넣는다. 날씨 관련 값에는 [완벽한 예보 가정]을 붙인다.
import sys, os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import numpy as np, pandas as pd

# 경로: 이 파일은 agent/tools/에 있고, agent 폴더 기준으로 읽고 쓴다.
#   읽기: inputs/results/*.csv   쓰기: 첫 번째 인자 폴더 (기본 figures_new/, 기존 figures/를 덮어쓰지 않음)
#   글꼴: tools/malgun.ttf, malgunbd.ttf (공개 저장소에는 올리지 않음). 없으면 시스템의 맑은 고딕을 찾는다.
# 사용: (agent 폴더에서) python tools/make_figs_malgun.py [출력폴더]
AGENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(AGENT, "inputs", "results") + os.sep
OUT = os.path.join(AGENT, sys.argv[1] if len(sys.argv) > 1 else "figures_new") + os.sep
os.makedirs(OUT, exist_ok=True)
for f in ("malgun.ttf", "malgunbd.ttf"):
    p = os.path.join(AGENT, "tools", f)
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": ["Malgun Gothic", "DejaVu Sans"], "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#b5b3ad",
    "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": False, "figure.facecolor": "white", "axes.facecolor": "white"})
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GREY, LGREY = "#9aa3ad", "#cfd4da"
BLUE, LBLUE, ORANGE, AQUA = "#2a78d6", "#86b6ef", "#eb6834", "#1baf7a"
W = 6.85  # A4 본문 폭(174mm)

def rd(f): return pd.read_csv(R + f, encoding="utf-8-sig")
def eok(x): return x / 1e8

def frame(fig, title, foot):
    fig.text(0.01, 0.985, "\n".join(textwrap.wrap(title, 46)), ha="left", va="top",
             fontsize=11, fontweight="bold", color=INK)
    fig.text(0.01, 0.012, "\n".join(textwrap.wrap(foot, 92)), ha="left", va="bottom", fontsize=7.5, color=MUTED, linespacing=1.4)

def save(fig, name, top, bottom=0.11):
    h = fig.get_size_inches()[1]
    fig.tight_layout(rect=(0, 0.42 / h, 1, top))
    fig.savefig(OUT + name, dpi=220, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

LOG = []

# ---------- 1 원점별 비용 ----------
e = rd("compare_per_origin.csv")
base, ens = e["직전7일평균"], e["앙상블(Chronos+Prophet)"]
fig, ax = plt.subplots(figsize=(W, 3.6))
x = np.arange(12)
ax.plot(x, eok(base), color=GREY, lw=2, marker="o", ms=5)
ax.plot(x, eok(ens), color=BLUE, lw=2, marker="o", ms=5)
ax.fill_between(x, eok(ens), eok(base), color=LBLUE, alpha=0.18, lw=0)
ax.set_xticks(x, [f"{i}월" for i in range(1, 13)])
ax.set_ylabel("원점별 총 비용 (억 원)")
ax.set_ylim(0, 5.2)
ax.yaxis.grid(True, color="#ecebe8", lw=0.6); ax.set_axisbelow(True)
ax.text(11.15, eok(base.iloc[11]) + 0.15, "직전 7일 평균", color=INK2, fontsize=8.5, ha="left")
ax.text(11.15, eok(ens.iloc[11]) - 0.25, "앙상블", color=BLUE, fontsize=8.5, ha="left")
d10 = base.iloc[9] - ens.iloc[9]
ax.annotate(f"10월 차이 {eok(d10):.2f}억 원\n(추석 연휴)", xy=(9, (eok(base.iloc[9]) + eok(ens.iloc[9])) / 2),
            xytext=(6.3, 3.6), fontsize=8.5, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax.set_xlim(-0.4, 12.4)
frame(fig, "앙상블은 2025년 12개 달 모두 직전 7일 평균보다 쌌고, 추석이 든 10월에 2.79억 원으로 차이가 가장 컸다",
      "단위: 억 원(원점별 총 비용, 소수 인원 기준). 원점 = 2025년 매월 1일, 예측 = 그달 끝까지. 출처: compare_per_origin.csv")
save(fig, "fig01_원점별비용.png", top=0.84)
LOG.append(("fig01_원점별비용.png", "compare_per_origin.csv",
            f"직전7일 합 {base.sum():,.0f} / 앙상블 합 {ens.sum():,.0f} / 10월 차이 {d10:,.0f}원 / 12개월 모두 앙상블<직전7일: {(ens<base).all()}"))

# ---------- 2 무료 개방일 비중 ----------
t = rd("오차_유형별.csv").set_index("유형")
fva = rd("FVA_앙상블.csv")
r1 = fva.iloc[0]
row_share = t.loc["무료 개방일", "행 수"] / t.loc["전체", "행 수"] * 100
b_share = r1["무료 개방일 비용 소수(원)"] / r1["총 비용 소수(원)"] * 100
e_share = t.loc["무료 개방일", "총 비용(원)"] / t.loc["전체", "총 비용(원)"] * 100
fig, ax = plt.subplots(figsize=(W, 2.6))
labels = ["평가 행 비중", "직전 7일 평균 비용 비중", "앙상블 비용 비중"]
vals = [row_share, b_share, e_share]; cols = [LGREY, GREY, BLUE]
y = np.arange(3)[::-1]
ax.barh(y, vals, color=cols, height=0.55)
for yi, v in zip(y, vals): ax.text(v + 0.6, yi, f"{v:.1f}%", va="center", fontsize=9, color=INK)
ax.set_yticks(y, labels); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.set_xlim(0, 36); ax.set_xlabel("무료 개방일이 차지하는 비중 (%)")
frame(fig, "무료 개방일은 평가 행의 7.6%지만 직전 7일 평균 비용의 30%를 만든다",
      f"단위: %. 무료 개방일 = 명절 연휴 블록 + 마지막 수요일(551행 / 7,203행). 출처: 오차_유형별.csv(행·앙상블), FVA_앙상블.csv 1행(직전 7일 평균)")
save(fig, "fig02_무료개방일비중.png", top=0.86, bottom=0.2)
LOG.append(("fig02_무료개방일비중.png", "오차_유형별.csv, FVA_앙상블.csv",
            f"행 551/7,203={row_share:.1f}% / 직전7일 510,909,652÷1,702,786,555={b_share:.1f}% / 앙상블 185,730,428÷865,671,728={e_share:.1f}%"))

# ---------- 3 임계비율 개념도 ----------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, 3.0), gridspec_kw=dict(width_ratios=[1, 2.2]))
ax1.bar([0, 1], [60, 15], color=[ORANGE, GREY], width=0.6)
ax1.set_xticks([0, 1], ["1명 모자람\n(Cu)", "1명 남음\n(Co)"])
for i, v in enumerate([60, 15]): ax1.text(i, v + 2, f"{v}만 원", ha="center", fontsize=9)
ax1.set_ylim(0, 72); ax1.set_yticks([]); ax1.spines["left"].set_visible(False)
xs = np.linspace(0.01, 3.2, 400)
from math import erf
s = 0.45; pdf = np.exp(-(np.log(xs)) ** 2 / (2 * s * s)) / (xs * s * np.sqrt(2 * np.pi))
q = np.exp(s * 0.8416)
ax2.plot(xs, pdf, color=INK2, lw=1.6)
ax2.fill_between(xs[xs <= q], pdf[xs <= q], color=LBLUE, alpha=0.55, lw=0)
ax2.axvline(q, color=BLUE, lw=1.8)
ax2.text(q + 0.06, pdf.max() * 0.85, "0.8 분위수 = 배치 인원 기준\n60 ÷ (60 + 15) = 0.8", color=BLUE, fontsize=8.5)
ax2.text(0.62, pdf.max() * 0.3, "80%", fontsize=10, ha="center", color=INK)
ax2.text(q + 0.45, pdf.max() * 0.32, "20%", fontsize=10, color=INK2)
ax2.set_yticks([]); ax2.spines["left"].set_visible(False); ax2.set_xticks([])
ax2.set_xlabel("하루 관람객 (개념도: 예시 분포, 실제 데이터 아님)")
frame(fig, "모자람 1명이 남음 1명보다 4배 비싸서, 인원은 관람객 분포의 0.8 분위수에 맞춘다",
      "단위: 만 원(1명·1일). 배치 인원 = 관람객 0.8 분위수 ÷ 2,000. 출처: 프로젝트 가이드 기본 가정(REPORT_SPEC 1-1). 오른쪽 분포는 설명용 예시")
save(fig, "fig03_임계비율_v2.png", top=0.84)
LOG.append(("fig03_임계비율_v2.png", "없음 (가이드 기본값)", "Cu 600,000원, Co 150,000원, 60÷75=0.8. 분포 곡선은 예시(데이터 아님)"))

# ---------- 4 모형별 비용 + 적중률 ----------
mc = rd("모형_비교_전체.csv").set_index("모형")
bo = e.drop(columns="origin").sum()
order = [("나이브", "나이브"), ("계절나이브7", "계절 나이브 7일"), ("직전7일평균", "직전 7일 평균 (현재 방식)"),
         ("서비스수준보정", "직전 7일 평균 + 서비스 수준 보정"), ("ETS", "ETS"), ("SARIMA", "SARIMA"), ("ARIMA", "ARIMA"),
         ("배율+월 (행6)", "배율 모형 + 월"), ("LightGBM 0.8 분위수", "LightGBM (0.8)"), ("Prophet", "Prophet"),
         ("Chronos-2 + 달력", "Chronos-2 + 달력"), ("앙상블(Chronos+Prophet)", "앙상블 (최종)")]
costs = []
for k, lab in order:
    c = bo[k] if k in ("ARIMA", "SARIMA", "ETS") else mc.loc[k, "총 비용 전체 소수(원)"]
    costs.append(c)
hits = [mc.loc[k, "적중률 전체(%)"] for k, _ in order]
grp = {"나이브": GREY, "계절나이브7": GREY, "직전7일평균": GREY, "서비스수준보정": GREY, "Prophet": LBLUE, "Chronos-2 + 달력": LBLUE, "앙상블(Chronos+Prophet)": BLUE}
idx = np.argsort(costs)[::-1]
order = [order[i] for i in idx]; costs = [costs[i] for i in idx]; hits = [hits[i] for i in idx]
fig, ax = plt.subplots(figsize=(W, 4.4))
y = np.arange(len(order))[::-1]
cols = [grp.get(k, LGREY) for k, _ in order]
ax.barh(y, eok(np.array(costs)), color=cols, height=0.62)
for yi, c, h in zip(y, costs, hits):
    ax.text(eok(c) + 0.2, yi, f"{eok(c):.2f}", va="center", fontsize=8.5, color=INK)
    ax.text(22.6, yi, f"{h:.1f}%", va="center", ha="right", fontsize=8.5, color=INK2)
ax.text(22.6, len(order) - 0.35, "적중률\n(목표 80%)", ha="right", va="bottom", fontsize=8, color=INK2)
ax.set_yticks(y, [l for _, l in order]); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.set_xlim(0, 23); ax.set_xlabel("총 비용 (억 원), 2025년 원점 12개 합")
frame(fig, "앙상블은 비용이 가장 낮고, 적중률은 82.0%로 목표 80%를 조금 넘는다",
      "단위: 억 원(소수 인원 기준). 적중률은 높을수록 좋은 지표라고 볼 수 없음(목표 80%). 출처: 모형_비교_전체.csv, ARIMA·SARIMA·ETS 비용은 compare_per_origin.csv 합")
save(fig, "fig04_모형별비용_v2.png", top=0.88, bottom=0.12)
LOG.append(("fig04_모형별비용_v2.png", "모형_비교_전체.csv, compare_per_origin.csv",
            "앙상블 865,671,727 / Chronos+달력 931,895,939 / Prophet 939,506,502 / LightGBM 1,100,868,588 / 직전7일 1,702,786,555 / ARIMA 1,513,682,679 / SARIMA 1,536,529,720 / ETS 1,649,316,571 / 적중률 앙상블 82.0, Chronos 80.6"))

# ---------- 5 부족/잉여 ----------
bt = rd("백테스트_비용.csv"); bt = bt[bt["규칙"] == "소수"].set_index("모형")
rows = [("직전7일평균", "직전 7일 평균"), ("앙상블(Chronos+Prophet)", "앙상블")]
fig, ax = plt.subplots(figsize=(W, 2.7))
y = np.array([1, 0])
for yi, (k, lab) in zip(y, rows):
    s_, o_ = bt.loc[k, "모자란 비용(원)"], bt.loc[k, "남는 비용(원)"]
    ax.barh(yi, eok(s_), color=ORANGE, height=0.55, edgecolor="white", lw=1.5)
    ax.barh(yi, eok(o_), left=eok(s_), color=GREY, height=0.55, edgecolor="white", lw=1.5)
    ax.text(eok(s_) / 2, yi, f"모자람 {eok(s_):.2f}", ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")
    ax.text(eok(s_) + eok(o_) / 2, yi, f"남음 {eok(o_):.2f}", ha="center", va="center", color=INK, fontsize=8.5)
    ax.text(eok(s_ + o_) + 0.2, yi, f"{eok(s_ + o_):.2f}억", va="center", fontsize=9, color=INK)
ax.set_yticks(y, [l for _, l in rows]); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.set_xlim(0, 19.5); ax.set_xlabel("총 비용 (억 원)")
sv = bt.loc["앙상블(Chronos+Prophet)", "모자란 비용(원)"]; sb = bt.loc["직전7일평균", "모자란 비용(원)"]
frame(fig, "앙상블은 남는 비용을 거의 늘리지 않고 모자란 비용을 65% 줄였다",
      "단위: 억 원(소수 인원 기준, 2025년 원점 12개). 모자람 1명 60만 원, 남음 1명 15만 원. 출처: 백테스트_비용.csv")
save(fig, "fig05_부족잉여비용.png", top=0.86, bottom=0.2)
LOG.append(("fig05_부족잉여비용.png", "백테스트_비용.csv (소수)",
            f"모자람 1,295,515,713 → 450,487,624 (−{(1-sv/sb)*100:.1f}%) / 남음 407,270,842 → 415,184,103"))

# ---------- 6 FVA 폭포 + 날씨 ----------
f = fva
tot = f["총 비용 소수(원)"].values
w = rd("날씨_완벽예보_근사.csv")
wthr = w.iloc[1]
labels = ["1 직전 7일\n평균", "2 서비스\n수준 보정", "3 과거\n관람객만", "4 예정\n휴관", "5 공휴일", "6 명절\n연휴", "7 마지막\n수요일",
          "최종\n앙상블", "8 휴관 이동·\n이웃 궁 휴관", "", "날씨\n[완벽한\n예보 가정]"]
fig, ax = plt.subplots(figsize=(W, 4.0))
xs = np.arange(len(labels))
ax.bar(0, eok(tot[0]), color=GREY, width=0.62)
cat = {1: LGREY, 2: BLUE, 3: AQUA, 4: AQUA, 5: AQUA, 6: AQUA}
for i in range(1, 7):
    ax.bar(i, eok(tot[i - 1] - tot[i]), bottom=eok(tot[i]), color=cat[i], width=0.62)
    ax.text(i, eok(tot[i - 1]) + 0.25, f"−{eok(tot[i-1]-tot[i]):.2f}", ha="center", fontsize=8, color=INK)
ax.bar(7, eok(tot[6]), color=BLUE, width=0.62)
ax.bar(8, max(eok(tot[7] - tot[6]), 0.12), bottom=eok(tot[6]), color=ORANGE, width=0.62)
ax.text(8, eok(tot[7]) + 0.3, f"+{(tot[7]-tot[6])/1e8:.3f}\n(+{tot[7]-tot[6]:,.0f}원)", ha="center", fontsize=7.5, color=INK)
ax.bar(10, eok(wthr["총 비용 소수(원)"]), color="white", edgecolor=MUTED, hatch="///", width=0.62, lw=0.8)
ax.text(10, eok(wthr["총 비용 소수(원)"]) + 0.25, f"{eok(wthr['총 비용 소수(원)']):.2f}", ha="center", fontsize=8, color=INK2)
ax.axvline(9, color="#d6d4cf", lw=0.8, ls="--")
ax.text(10, 11.2, "합산·비교하지\n않는 사후 근사", ha="center", fontsize=7.5, color=MUTED)
ax.text(0, eok(tot[0]) + 0.25, f"{eok(tot[0]):.2f}", ha="center", fontsize=8.5, color=INK)
ax.text(7, eok(tot[6]) + 0.25, f"{eok(tot[6]):.2f}", ha="center", fontsize=8.5, color=INK, fontweight="bold")
for i in range(0, 7):
    ax.plot([i + 0.31, i + 0.69], [eok(tot[i])] * 2, color=MUTED, lw=0.7)
ax.set_xticks(xs, labels, fontsize=7.5); ax.tick_params(axis="x", length=0)
ax.set_ylabel("총 비용 (억 원)"); ax.set_ylim(0, 19)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=LGREY, label="서비스 수준 보정"), Patch(color=BLUE, label="모형(과거 관람객)"),
                   Patch(color=AQUA, label="달력 정보"), Patch(color=ORANGE, label="비용 증가")],
          loc="upper center", bbox_to_anchor=(0.6, 1.0), fontsize=7.5, frameon=False, ncol=2)
frame(fig, "절감액 8.37억 원 중 56%는 모형, 32%는 달력 정보, 12%는 서비스 수준 보정에서 나왔고, 이웃 궁 휴관은 오히려 비용을 늘렸다",
      "단위: 억 원(소수 인원 기준, 2025년 원점 12개). FVA 7행 = 865,671,730원(검산값 865,671,727원과 계산 차이 3원). 출처: FVA_앙상블.csv, 날씨_완벽예보_근사.csv(다른 달로 학습)")
save(fig, "fig06_FVA폭포.png", top=0.86, bottom=0.17)
LOG.append(("fig06_FVA폭포.png", "FVA_앙상블.csv, 날씨_완벽예보_근사.csv",
            "행1 1,702,786,555 → −102,798,587(12.3%) −467,695,061(55.9%) −44,409,280 −150,233,313 −43,560,954 −28,417,630(4~7행 합 266,621,177, 31.9%) → 865,671,730 / 8행 +1,527,342 / 날씨 [완벽한 예보 가정] 846,029,975"))

# ---------- 7 운영 방안 ----------
op = rd("운영방안_비교.csv")
names = ["1. 월 1회", "2. 월 1회 + 공지 증원", "3. 월 1회 + 공지 증원 + 수요일 하한  [1단계]", "4. 주 1회",
         "5. 주 1회 + 공지 증원 + 수요일 하한  [3단계]", "6. 궁·종묘 주 1회 + 왕릉 월 1회", "7. 6 + 공지 증원 + 수요일 하한  [2단계]"]
know = ["약 16일 전", "약 16일 전", "약 16일 전", "4일 전", "4일 전", "4일 / 16일 전", "4일 / 16일 전"]
c = op["총 비용 소수(원)"].values
fig, ax = plt.subplots(figsize=(W, 3.6))
y = np.arange(7)[::-1]
cols = [GREY, LGREY, BLUE, GREY, BLUE, LGREY, BLUE]
ax.barh(y, eok(c), color=cols, height=0.6)
for yi, v, k in zip(y, c, know):
    ax.text(eok(v) + 0.09, yi, f"{eok(v):.2f}억", va="center", fontsize=8.5, color=INK)
    ax.text(10.6, yi, k, va="center", ha="right", fontsize=8, color=INK2)
ax.text(10.6, 7.0, "근무자가 일정을\n아는 시점(평균)", ha="right", va="center", fontsize=7.5, color=INK2)
ax.axvline(eok(c[3]), color=MUTED, lw=0.8, ls="--")
ax.set_yticks(y, names, fontsize=8); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.set_xlim(6, 10.7); ax.set_xlabel("총 비용 (억 원, 축은 6억 원부터)")
frame(fig, "월 1회 확정에 공지 증원과 수요일 하한만 더해도 주 1회 확정보다 싸다",
      "단위: 억 원(소수 인원 기준). 공통 평가일 2025-01-06~12-31(7,088행), 공지 후 증원 준비 14일. 점선 = 주 1회. 출처: 운영방안_비교.csv")
save(fig, "fig07_운영방안비용.png", top=0.88, bottom=0.14)
LOG.append(("fig07_운영방안비용.png", "운영방안_비교.csv",
            f"방안1 860,058,276 / 방안3 780,789,064 / 방안4 783,167,238 (3이 {c[3]-c[2]:,.0f}원 쌈) / 방안5 697,035,657 / 방안7 725,575,571"))

# ---------- 8 상위 10건 ----------
tp = rd("오차_상위10건.csv")
cause = {1: "코리아 그랜드 페스티벌", 2: "종묘대제", 3: "추석 연휴", 4: "추석 연휴", 5: "코리아 그랜드 페스티벌", 6: "추석 연휴",
         7: "코리아 그랜드 페스티벌", 8: "코리아 그랜드 페스티벌", 9: "추석 연휴", 10: "코리아 그랜드 페스티벌"}
fig, ax = plt.subplots(figsize=(W, 3.9))
y = np.arange(10)[::-1]
for yi, (_, r) in zip(y, tp.iterrows()):
    col = AQUA if "추석" in cause[r["순위"]] else ORANGE
    ax.plot([r["예측 관람객"] / 1e4, r["실제 관람객"] / 1e4], [yi, yi], color="#d6d4cf", lw=2.2, zorder=1)
    ax.scatter(r["예측 관람객"] / 1e4, yi, s=42, color=GREY, zorder=2, edgecolor="white", lw=1.5)
    ax.scatter(r["실제 관람객"] / 1e4, yi, s=46, color=col, zorder=3, edgecolor="white", lw=1.5)
    ax.text(7.25, yi, f"−{r['모자란 인원']:.1f}명", va="center", fontsize=8, color=INK)
ax.set_yticks(y, [f"{r['날짜'][5:].replace('-', '/')}({r['요일']}) {r['개소']} · {cause[r['순위']]}" for _, r in tp.iterrows()], fontsize=7.8)
ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.set_xlim(0, 7.6); ax.set_xlabel("하루 관람객 (만 명)")
ax.text(7.25, 10.0, "모자란 인원", fontsize=7.5, color=INK2, va="center")
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=GREY, label="예측(0.8 분위수)"),
                   plt.Line2D([], [], marker="o", ls="", color=ORANGE, label="실제 · 행사"),
                   plt.Line2D([], [], marker="o", ls="", color=AQUA, label="실제 · 추석 연휴")],
          loc="lower left", bbox_to_anchor=(0.0, 1.0), fontsize=7.5, frameon=False, ncol=3)
frame(fig, "인력이 가장 많이 모자란 10건은 모두 근무표 확정 전에 알 수 있던 행사·추석이었다",
      "단위: 만 명(관람객), 명(인력). 원인 출처: 궁능유적본부 공지(코리아 그랜드 페스티벌), 국가유산청 공지(종묘대제), 달력 파일(추석). 수치 출처: 오차_상위10건.csv")
save(fig, "fig08_부족상위10건.png", top=0.88, bottom=0.14)
LOG.append(("fig08_부족상위10건.png", "오차_상위10건.csv (+원인은 REPORT_SPEC 5-7 출처)",
            "1위 11/08 덕수궁 실제 66,257 / 예측 26,551 / 19.85명 … 10위 11/09 덕수궁 11.27명. 행사 6건, 추석 4건"))

# ---------- 9 가정 바꾸기 ----------
a = rd("가정_바꾸기.csv")
lab = ["기본", "무료 개방일\n모자람 비용 2배", "1명당 1,500명", "둘 다"]
fig, ax = plt.subplots(figsize=(W, 3.1))
x = np.arange(4); wd = 0.36
bb = a["직전 7일 평균 총 비용(원)"].values; ee = a["앙상블 총 비용(원)"].values; rr = a["절감 비율(%)"].values
ax.bar(x - wd / 2 - 0.01, eok(bb), wd, color=GREY, label="직전 7일 평균")
ax.bar(x + wd / 2 + 0.01, eok(ee), wd, color=BLUE, label="앙상블")
for i in range(4):
    ax.text(x[i] - wd / 2, eok(bb[i]) + 0.3, f"{eok(bb[i]):.2f}", ha="center", fontsize=8)
    ax.text(x[i] + wd / 2, eok(ee[i]) + 0.3, f"{eok(ee[i]):.2f}", ha="center", fontsize=8)
    ax.text(x[i], eok(bb[i]) + 3.0, f"절감 {rr[i]:.1f}%", ha="center", fontsize=9, fontweight="bold", color=INK)
ax.set_xticks(x, lab); ax.tick_params(axis="x", length=0)
ax.set_ylabel("총 비용 (억 원)"); ax.set_ylim(0, 34)
ax.legend(loc="upper left", fontsize=8, frameon=False)
frame(fig, "무료 개방일 모자람 비용을 2배로 보면 절감률은 56.6%로 커지고, 1명당 1,500명이어도 49.2%로 같다",
      "단위: 억 원(소수 인원 기준). 가정 1·3은 예측(0.8 분위수)을 그대로 두고 비용만 다시 계산. 출처: 가정_바꾸기.csv")
save(fig, "fig09_가정바꾸기.png", top=0.86, bottom=0.17)
LOG.append(("fig09_가정바꾸기.png", "가정_바꾸기.csv",
            "기본 1,702,786,555/865,671,727 49.2% · 2배 2,204,566,145/957,457,599 56.6% · 1,500명 2,270,382,073/1,154,228,970 49.2% · 둘 다 2,939,421,526/1,276,610,132 56.6%"))

# ---------- 10 개소별 배율 ----------
m = rd("무료개방_효과_개소별.csv").sort_values("명절 연휴 배율")
fig, ax = plt.subplots(figsize=(W, 5.0))
y = np.arange(len(m))
for yi, (_, r) in zip(y, m.iterrows()):
    lo, hi = sorted([r["마지막 수요일 배율"], r["명절 연휴 배율"]])
    ax.plot([lo, hi], [yi, yi], color="#e4e2dd", lw=1.5, zorder=1)
ax.scatter(m["마지막 수요일 배율"], y, s=34, color=BLUE, zorder=3, edgecolor="white", lw=1.2, label="마지막 수요일")
ax.scatter(m["명절 연휴 배율"], y, s=34, color=ORANGE, zorder=3, edgecolor="white", lw=1.2, label="명절 연휴")
ax.axvline(1, color=MUTED, lw=0.8, ls="--"); ax.text(1.03, len(m) - 0.4, "평상시(1배)", fontsize=7.5, color=MUTED)
ax.set_yticks(y, [f"{s} ({g})" for s, g in zip(m["개소"], m["구분"])], fontsize=7.8)
ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.set_xlabel("무료 개방일 평균 ÷ 같은 요일 일반 개방일 평균 (배)")
ax.set_xlim(0.5, 8.2)
mn = m["마지막 수요일 배율"].min(); mx = m["명절 연휴 배율"].max()
ax.annotate(f"의릉 명절 {mx:.2f}배", xy=(mx, y[-1]), xytext=(6.2, y[-1] - 2.5), fontsize=8, color=INK2,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
ia = int(np.where(m["개소"].values == "영휘원")[0][0])
ax.annotate(f"영휘원 수요일 {mn:.2f}배", xy=(mn, y[ia]), xytext=(2.6, y[ia] - 1.6), fontsize=8, color=INK2,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
ax.legend(loc="lower right", fontsize=8, frameon=False)
frame(fig, "무료 개방 효과는 개소마다 1배 미만에서 7배 넘게 달라, 개소를 합치면 효과가 뭉개진다",
      "단위: 배(평상시 대비). 2023~2025년 개방일, 명절 배율에는 연휴 자체 효과 포함. 출처: 무료개방_효과_개소별.csv")
save(fig, "fig10_개소별무료개방배율.png", top=0.9, bottom=0.1)
LOG.append(("fig10_개소별무료개방배율.png", "무료개방_효과_개소별.csv",
            f"최소 영휘원 수요일 {mn:.2f} / 최대 의릉 명절 {mx:.2f} / 종묘 4.84·5.47 / 경복궁 1.98·4.40"))

for l in LOG: print(" | ".join(l))
