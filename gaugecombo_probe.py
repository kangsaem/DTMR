"""(gaugecombo) 4개 이상 날의 항목 구성 + 시장 위험 지표 6개 전체 점검 + 대체 후보(2026-11-25 사용자). 코스피 2000~ 기준, 켜진 날 전부(날 기준)와 처음 켜진 날(구간 기준) 둘 다.
좋은 위험 항목 = 켜진 날 60일 안 -10% 하락 확률이 아무 날보다 확실히 높고, 60일 뒤 평균이 아무 날보다 낮음. 너무 드물면(구간 2~3번) 쓸모 적음.
자료: 코스피 FDR KS11 · 미국채 10년 FRED DGS10(리포트는 야후 ^TNX, 값 거의 같음) · 달러원 FDR USD/KRW
· 내 종목 역배열 = tickers.json 종목의 과거 주가(지금 목록 기준이라 생존 편향) · 신용잔고/예탁금 = 리포트와 같은 자료(약 5년뿐)"""
import json, numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m

ks = fdr.DataReader("KS11", "1998-01-01")["Close"].dropna()
I = ks.index; n = len(ks); c = ks.values
fwd60 = pd.Series([(c[i + 60] / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
dd60 = pd.Series([(c[i + 1:i + 61].min() / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
rsi = m.rsi(ks); d50 = ks / ks.rolling(50).mean() * 100; d200 = ks / ks.rolling(200).mean() * 100
wk = ks.groupby(pd.Grouper(freq="W-FRI")).last().dropna(); wrsi = m.rsi(wk).reindex(I, method="ffill")

def ext(code, start="1998-01-01"):
    try:
        s = fdr.DataReader(code, start); s = s.iloc[:, 0] if "Close" not in s else s["Close"]
        return pd.to_numeric(s, errors="coerce").dropna()
    except Exception as e:
        print("자료 실패", code, e); return pd.Series(dtype=float)
t10 = ext("FRED:DGS10"); fx = ext("USD/KRW")
y_chg10 = (t10 - t10.shift(10)).reindex(I, method="ffill"); y_chg20 = (t10 - t10.shift(20)).reindex(I, method="ffill")
fx_r = fx.reindex(I, method="ffill"); fx20 = (fx_r / fx_r.shift(20) - 1) * 100

# 내 종목 일봉 역배열 비율(5일선 < 10일선, 리포트 cross_state와 같음)
tk = [t for t in json.load(open("tickers.json", encoding="utf-8")) if t.get("code")]
arr = {}
for t in tk:
    try:
        p = m.load_prices(t["code"])["Close"].dropna()
        p.index = pd.to_datetime(p.index).tz_localize(None) if getattr(p.index, "tz", None) else pd.to_datetime(p.index)
        p = p[~p.index.duplicated()]
        if len(p) > 30: arr[t["code"]] = (p.rolling(5).mean() < p.rolling(10).mean()).astype(float).where(p.rolling(10).mean().notna())
    except Exception as e:
        pass
A = pd.DataFrame(arr).reindex(I).astype(float)
cnt = A.notna().sum(axis=1); bear = (A.sum(axis=1) / cnt).where(cnt >= 10)
print(f"내 종목 {len(arr)}/{len(tk)}개 받음 · 10개 이상 있는 첫날 {bear.dropna().index[0]:%Y-%m-%d}" if bear.notna().any() else "내 종목 자료 없음")

# 신용잔고/예탁금 비율 백분위(그날까지 최대 5년 안, 리포트 credit_hist와 같음)
cpct = pd.Series(np.nan, index=I)
try:
    cred, dep = m.credit_tables(); r = m.credit_series(cred, dep)["ratio"]
    v, ix = r.values, r.index
    pc = pd.Series([float((v[(ix >= ix[i] - pd.DateOffset(years=m.CREDIT_YEARS)) & (ix <= ix[i])] <= v[i]).mean() * 100) if i >= 120 else np.nan for i in range(len(r))], index=ix)
    cpct = pc.reindex(I, method="ffill", limit=5)
    print(f"신용 비율 {ix[0]:%Y-%m-%d} ~ {ix[-1]:%Y-%m-%d} ({len(r)}일) · 백분위는 120일 이후부터")
except Exception as e:
    print("신용 자료 실패", e)


# 외국인(foreignrisk_probe와 같음)
import time, requests
from concurrent.futures import ThreadPoolExecutor
have = json.load(open("results/foreign_kospi.json"))
Hh = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}
need = [d.strftime("%Y%m%d") for d in I if d >= pd.Timestamp("2026-10-15") and d.strftime("%Y%m%d") not in have]
def one(d):
    for k in range(3):
        try:
            j = requests.get(f"https://m.stock.naver.com/api/index/KOSPI/trend?bizdate={d}", headers=Hh, timeout=15).json()
            return d, (float(str(j["foreignValue"]).replace(",", "").replace("+", "")) if j.get("bizdate") == d else None)
        except Exception:
            time.sleep(1 + k)
    return d, None
with ThreadPoolExecutor(6) as ex:
    for d, v in ex.map(one, need):
        if v is not None: have[d] = v
fo = pd.Series({pd.Timestamp(k): v for k, v in have.items()}).sort_index()
F0 = fo[fo != 0].index[0]; fo = fo[fo.index >= F0].reindex(I); fo[fo.index >= F0] = fo[fo.index >= F0].fillna(0)
f20 = fo.rolling(20).sum(); k20 = (ks / ks.shift(20) - 1) * 100
near_hi = ks >= ks.rolling(252, min_periods=200).max() * 0.97

B = {"50일 이격 120↑": d50 >= 120, "200일 이격 150↑": d200 >= 150, "금리 20일 +0.5%p↑": y_chg20 >= 0.5,
     "신용 상위 10%": cpct >= 90, "고점 근처 외국인 20일 매도": near_hi & (f20 < 0)}
SIX = {"200일 이격 130↑": d200 >= 130, "50일 이격 115↑": d50 >= 115, "급등 중 외국인 매도": (k20 >= 5) & (f20 < 0), "내 종목 70% 역배열": bear >= 0.7}
NOWSET = {"RSI 70↑": rsi >= 70, "50일 이격 120↑": d50 >= 120, "200일 이격 150↑": d200 >= 150, "금리 10일 +0.3%p↑": y_chg10 >= 0.3,
          "내 종목 70% 역배열": bear >= 0.7, "신용 상위 10%": cpct >= 90}
def runs(on):
    r, cur = [], None
    for i in range(len(on)):
        if on[i]:
            if cur and i - cur[1] <= 20: cur[1] = i
            else:
                if cur: r.append(cur)
                cur = [i, i]
    if cur: r.append(cur)
    return r
def report(nm, items, since="2010-01-01"):
    sc = sum(v.fillna(False).astype(int) for v in items.values()).loc[since:]
    ok = fwd60.loc[since:].notna(); bd = dd60.loc[since:][ok]
    print(f"\n■ {nm} — " + " · ".join(items))
    print(f"   아무 날 -10%↓ {(bd <= -10).mean() * 100:.0f}% · 60일 {fwd60.loc[since:][ok].mean():+.1f}%")
    for lo, hi, lv in ((0, 0, "0개"), (1, 6, "1개 이상"), (2, 6, "2개 이상"), (3, 6, "3개 이상"), (4, 6, "4개 이상"), (5, 6, "5개 이상"), (6, 6, "6개")):
        msk = (sc >= lo) & (sc <= hi); mm = msk & ok
        on = msk.values; rr = runs(on) if lo >= 2 else []
        if mm.sum():
            f, dd = fwd60.loc[since:][mm], dd60.loc[since:][mm]
            print(f"   {lv:<11} {int(msk.sum()):>4}일({msk.mean() * 100:4.1f}%) | 60일 {f.mean():+5.1f}% · -10%↓ {(dd <= -10).mean() * 100:3.0f}% · 최대하락 {dd.mean():+5.1f}%"
                  + (f" | {len(rr)}구간, 최근 {', '.join(f'{sc.index[a]:%y.%m}' for a, b in rr[-4:])}" if rr else ""))
        else:
            print(f"   {lv:<11} {int(msk.sum()):>4}일")
    print(f"   지금 {int(sc.iloc[-1])}개 켜짐: " + ", ".join(k for k, v in items.items() if bool(v.fillna(False).iloc[-1])))
def detail(nm, items, since="2010-01-01", th=4):
    on = {k: v.fillna(False).astype(bool).loc[since:] for k, v in items.items()}
    sc = sum(v.astype(int) for v in on.values())
    days = sc[sc >= th].index
    print(f"\n■ {nm} — {th}개 이상 {len(days)}일")
    sets = {}
    for d in days:
        key = " + ".join(k for k in items if on[k][d]); sets.setdefault(key, []).append(d)
    for key, ds in sorted(sets.items(), key=lambda x: x[1][0]):
        print(f"   {len(ds):>3}일 ({ds[0]:%y.%m.%d} ~ {ds[-1]:%y.%m.%d}) {key}")
y_lv = t10.reindex(I, method="ffill")
A6 = {"50일 이격 120↑": d50 >= 120, "200일 이격 150↑": d200 >= 150, "금리 20일 +0.5%p↑": y_chg20 >= 0.5, "미국 10년물 5% 이상": y_lv >= 5.0,
      "고점 근처 외국인 20일 매도": near_hi & (f20 < 0), "내 종목 70% 역배열": bear >= 0.7}
print("(점수 = 켜진 항목 수, 자료 없는 항목은 꺼진 것으로 셈. 외국인 2005~, 내 종목 2014~)")
for since in ("2000-01-01", "2010-01-01"):
    print(f"\n######## {since[:4]}~")
    report("지금 6개", NOWSET, since)
    report("A안 6개", A6, since)
for th in (2, 3, 4):
    detail("A안 6개", A6, "2000-01-01", th)
