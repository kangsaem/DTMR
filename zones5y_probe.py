"""(zones5y) 앱 지수 차트 칠하기 기준 점검(2026-11-25 사용자: 위험은 너무 많이, 바닥은 너무 적게 칠해짐).
앱과 같은 항목으로 날마다 위험·바닥 켜진 개수를 세고, 'N개 이상' 마다 칠해지는 날 비율 · 구간 수 · 그 뒤 60일 결과.
위험 = 50일 이격 120↑, 200일 이격 150↑, 미국채10년 20일 +0.5%p↑, 10년 5%↑, (내 종목 70% 역배열), 52주 고점 -3% 안 + 외국인 20일 순매도
바닥 = 50일 이격 90↓, RSI 35↓, 고점 -20%↓ + 저점 뒤 20일↑, VIX 30↑, (내 종목 30% RSI 35↓), VKOSPI 바닥 안정
내 종목 = tickers.json 지금 목록(생존 편향) — '시장만'과 '내 종목 포함' 둘 다."""
import json, numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m, vkospi, foreign

ks = fdr.DataReader("KS11", "2004-01-01")["Close"].dropna()
I = ks.index; n = len(ks); c = ks.values
fwd60 = pd.Series([(c[i + 60] / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
dd60 = pd.Series([(c[i + 1:i + 61].min() / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
up60 = pd.Series([(c[i + 1:i + 61].max() / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
rs = m.rsi(ks); d50 = ks / ks.rolling(50).mean() * 100; d200 = ks / ks.rolling(200).mean() * 100
hi = ks.rolling(250, min_periods=1).max(); fh = (ks / hi - 1) * 100
lo_pos = ks.rolling(250, min_periods=1).apply(lambda a: len(a) - 1 - int(np.argmin(a)), raw=True)

def ext(code):
    try:
        s = fdr.DataReader(code, "2003-01-01"); s = s.iloc[:, 0] if "Close" not in s else s["Close"]
        return pd.to_numeric(s, errors="coerce").dropna()
    except Exception as e:
        print("자료 실패", code, e); return pd.Series(dtype=float)
t10 = ext("FRED:DGS10"); vix = ext("FRED:VIXCLS")
y20 = (t10 - t10.shift(20)).reindex(I, method="ffill"); ylv = t10.reindex(I, method="ffill"); vx = vix.reindex(I, method="ffill")

f = foreign.series() if hasattr(foreign, "series") else None
if f is None or len(f) == 0:
    f = pd.read_csv("data/foreign_kospi.csv", index_col=0, parse_dates=True)["foreign"]
fj = json.load(open("results/foreign_kospi.json"))
fa = pd.Series({pd.Timestamp(k): float(v) for k, v in fj.items()}).sort_index()
fa = fa.where(fa.index >= "2006-01-01")
f = pd.concat([fa[fa.index < f.index[0]], f]).sort_index()
f = f[~f.index.duplicated(keep="last")].reindex(I)
f20 = f.rolling(20, min_periods=18).sum().where(f.notna())
fr_on = (fh >= -3) & (f20 < 0)

try:
    vr = m.vk_rule(vkospi.series(), ks); vk_on = vr["on"].reindex(I).fillna(False).astype(bool)
except Exception as e:
    print("VKOSPI 실패", e); vk_on = pd.Series(False, index=I)

tk = [t for t in json.load(open("tickers.json", encoding="utf-8")) if t.get("code")]
bear_d, low_d = {}, {}
for t in tk:
    try:
        p = m.load_prices(t["code"])["Close"].dropna()
        p.index = pd.to_datetime(p.index).tz_localize(None) if getattr(p.index, "tz", None) else pd.to_datetime(p.index)
        p = p[~p.index.duplicated()]
        if len(p) > 30:
            ok = p.rolling(10).mean().notna()
            bear_d[t["code"]] = (p.rolling(5).mean() <= p.rolling(10).mean()).astype(float).where(ok)
            r = m.rsi(p); low_d[t["code"]] = (r <= 35).astype(float).where(r.notna())
    except Exception:
        pass
B_ = pd.DataFrame(bear_d).reindex(I, method="ffill", limit=3); L_ = pd.DataFrame(low_d).reindex(I, method="ffill", limit=3)
cb, cl = B_.notna().sum(axis=1), L_.notna().sum(axis=1)
mine_bear = ((B_.sum(axis=1) / cb) >= 0.7) & (cb >= 10)
mine_low = ((L_.sum(axis=1) / cl) >= 0.3) & (cl >= 10)
print(f"내 종목 {len(bear_d)}/{len(tk)}개")

R = pd.DataFrame({"이격120": d50 >= 120, "200일150": d200 >= 150, "금리20일+0.5": y20 >= 0.5, "금리5%": ylv >= 5,
                  "내종목역배열": mine_bear, "외국인": fr_on.fillna(False)}).fillna(False)
Bt = pd.DataFrame({"이격90": d50 <= 90, "RSI35": rs <= 35, "고점-20+20일": (fh <= -20) & (lo_pos >= 20), "VIX30": vx >= 30,
                   "내종목RSI": mine_low, "VKOSPI": vk_on}).fillna(False)

def runs(mask):
    s = mask.astype(int); return int(((s.diff() == 1) | ((s == 1) & (s.shift().isna()))).sum())

def table(kind, df, frm, label):
    d = df[df.index >= frm]; cnt = d.sum(axis=1)
    ok = fwd60.reindex(d.index).notna()
    base_dd = (dd60.reindex(d.index)[ok] <= -10).mean() * 100; base_f = fwd60.reindex(d.index)[ok].mean()
    base_up = (up60.reindex(d.index)[ok] >= 10).mean() * 100
    print(f"\n[{kind} · {label} · {frm[:4]}~ · {len(d)}일] 아무 날: 60일 안 -10% {base_dd:.0f}% · +10% {base_up:.0f}% · 60일 뒤 평균 {base_f:+.1f}%")
    print("  항목별 켜진 날 %: " + ", ".join(f"{k} {d[k].mean()*100:.0f}" for k in d.columns))
    for k in range(1, 6):
        msk = cnt >= k
        if not msk.any(): print(f"  {k}개↑: 없음"); continue
        mm = msk & ok
        print(f"  {k}개↑: 칠한 날 {msk.mean()*100:4.1f}% · 구간 {runs(msk):3d}번 · 60일 안 -10% {(dd60[mm.reindex(dd60.index, fill_value=False)] <= -10).mean()*100:3.0f}%"
              f" · +10% {(up60[mm.reindex(up60.index, fill_value=False)] >= 10).mean()*100:3.0f}% · 60일 뒤 평균 {fwd60[mm.reindex(fwd60.index, fill_value=False)].mean():+5.1f}% (결과 있는 날 {int(mm.sum())})")

for frm in ["2021-11-25", "2010-01-01"]:
    for kind, df in [("위험", R), ("바닥", Bt)]:
        table(kind, df.drop(columns=[c for c in df.columns if c.startswith("내종목")]), frm, "시장만(옛날 앱과 같음)")
        table(kind, df, frm, "내 종목 포함")

# 최근 5년 연도별 칠한 날 %(시장만)
print("\n[연도별 칠한 날 % · 시장만]")
Rm, Bm = R.drop(columns=["내종목역배열"]).sum(axis=1), Bt.drop(columns=["내종목RSI"]).sum(axis=1)
for y in range(2021, 2027):
    sel = I.year == y
    print(f"  {y}: 위험 1↑ {(Rm[sel]>=1).mean()*100:3.0f} · 2↑ {(Rm[sel]>=2).mean()*100:3.0f} · 3↑ {(Rm[sel]>=3).mean()*100:3.0f}"
          f"  |  바닥 2↑ {(Bm[sel]>=2).mean()*100:3.0f} · 3↑ {(Bm[sel]>=3).mean()*100:3.0f} · 4↑ {(Bm[sel]>=4).mean()*100:3.0f}")
