import warnings, time
import numpy as np, pandas as pd
from scipy.stats import norm
from statsmodels.tsa.statespace.sarimax import SARIMAX
warnings.filterwarnings("ignore")
df = pd.read_csv("train_2023_2025_core_v2.csv", parse_dates=["date"]).sort_values(["site","date"])
SITES = ["경복궁","덕수궁","창덕궁","창경궁","종묘"]
ORIG = pd.date_range("2025-01-01","2025-12-01",freq="MS")
EXOG = ["is_holiday","is_myeongjeol","is_last_wednesday","is_weekend"]
z = norm.ppf(0.8)
def cost(y,q): n,p=y/2000,q/2000; return 600000*np.clip(n-p,0,None)+150000*np.clip(p-n,0,None)
lg = pd.read_csv("bt12_predictions.csv", parse_dates=["date","origin"])
rows=[]; t0=time.time()
for s in SITES:
    g = df[df.site==s].set_index("date").asfreq("D")
    y = np.log1p(g["total"].where(g["actual_closed"]==0))    # 휴관일은 결측 (칼만 필터가 건너뜀)
    X = g[EXOG].astype(float)
    for O in ORIG:
        end = O + pd.offsets.MonthEnd(0)
        ytr = y[:O - pd.Timedelta(days=1)]
        m = SARIMAX(ytr, exog=X.loc[ytr.index], order=(1,0,1), seasonal_order=(1,0,1,7), trend="c",
                    enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=200)
        f = m.get_forecast(steps=(end-O).days+1, exog=X.loc[O:end])
        mu, sd = f.predicted_mean, np.sqrt(f.var_pred_mean)
        q80 = np.expm1(mu + z*sd)
        rows.append(pd.DataFrame({"site":s,"origin":O,"date":q80.index,"sarimax":q80.values}))
print("fit time", round(time.time()-t0), "s")
sx = pd.concat(rows)
m = sx.merge(lg, on=["site","origin","date"])
m = m[m.is_open]
m.loc[m.planned_closed==1,"sarimax"] = 0
out={}
for c in ["직전 7일 평균","개소별 배율 모형","LightGBM","sarimax"]:
    out[c]={"비용(백만원)":cost(m.total,m[c]).sum()/1e6,"적중률(%)":(m.total<=m[c]).mean()*100,"WAPE(%)":(m.total-m[c]).abs().sum()/m.total.sum()*100}
print(len(m),"행 (궁 4곳 + 종묘, 원점 12개, 개방일)")
print(pd.DataFrame(out).T.round(1))
per = m.groupby("origin").apply(lambda d: pd.Series({c: cost(d.total,d[c]).sum()/1e6 for c in ["직전 7일 평균","LightGBM","sarimax"]})).round(1)
per.index=per.index.strftime("%m"); print(per.T)
print("SARIMAX가 LightGBM보다 싼 원점:", (per.sarimax<per.LightGBM).sum(), "/ 12")
pd.set_option("display.width",250)
print(per.T.to_string())
print(m.nlargest(5,"sarimax")[["site","origin","date","total","sarimax","LightGBM"]])
ok = m[~((m.origin==m.loc[m.sarimax.idxmax(),"origin"])&(m.site==m.loc[m.sarimax.idxmax(),"site"]))]
print("폭주한 원점·개소 1건 제외:", {c: round(cost(ok.total,ok[c]).sum()/1e6,1) for c in ["직전 7일 평균","LightGBM","sarimax"]})
