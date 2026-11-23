"""VKOSPI 기울기 반전 확인(2026-11-23): 숫자 바꿔도 유지되는지 + 가격 조건 '20일선 위만'(M) vs 전체(P) vs 없음
기울기 반전 = 급등(60일 최고 ≥30, 20일 최고 ≥ 120일 중간값×A) 뒤 5일 변화가 B일 연속 −, 20일선 아래 — 꺼짐→켜짐, 20일 쿨다운.
M = 신호 뒤 20거래일 안에 코스피 종가 ≥ 20일선인 첫날(안 맞으면 버림)"""

import numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m, vkospi

vk = vkospi.series()
ks = fdr.DataReader("KS11", "2009-01-01")["Close"].dropna()
vk = vk[vk.index.isin(ks.index)]
k = ks.reindex(vk.index)                       # 같은 날짜만
ks_i = {d: i for i, d in enumerate(ks.index)}
COOL = 20

# ---- 규칙 (Series[bool], 날짜별 '켜짐 상태')
ma20, sd20 = vk.rolling(20).mean(), vk.rolling(20).std()
mx60 = vk.rolling(60, min_periods=20).max()
def edge(st):                                   # 꺼짐 → 켜짐
    st = st.fillna(False).astype(bool)
    return st & ~st.shift(1, fill_value=False)

R = {}
R["0 지금 규칙"] = edge(m.vkospi_on(vk).astype(bool))
for A in (1.3, 1.5, 1.8):
    for B in (2, 3, 4):
        sp = (mx60 >= 30) & (vk.rolling(20).max() >= vk.rolling(120, min_periods=60).median() * A)
        R[f"3 기울기 A{A} B{B}"] = edge(sp & (vk.diff(5) < 0).rolling(B).min().astype(bool) & (vk < ma20))
for W in (3, 10):
    sp = (mx60 >= 30) & (vk.rolling(20).max() >= vk.rolling(120, min_periods=60).median() * 1.5)
    R[f"3 기울기 A1.5 B3 변화{W}일"] = edge(sp & (vk.diff(W) < 0).rolling(3).min().astype(bool) & (vk < ma20))
low20 = k.rolling(20).min()
price_ok = (k.rolling(20).apply(lambda x: np.argmin(x) == 0, raw=True) == 1) & (k >= k.rolling(20).mean())   # 20일 안 신저점 없음(최저가 20일 전 첫날) + 20일선 위

def combo(st, ok_s=None):   # 신호 뒤 20거래일 안에 가격 조건이 처음 맞는 날로 미룸(안 맞으면 버림)
    out = pd.Series(False, index=st.index); ok = (price_ok if ok_s is None else ok_s).reindex(st.index).fillna(False).astype(bool)
    idx = list(st.index)
    for d in st[st.fillna(False).astype(bool)].index:
        i = idx.index(d)
        for j in range(i, min(i + 21, len(idx))):
            if ok.iloc[j]: out.iloc[j] = True; break
    return out


def signals(st):
    out, last = [], None
    for d in st[st].index:
        i = ks_i[d]
        if last is not None and i - last < COOL: continue
        out.append(d); last = i
    return out

def stats(days):
    rows = []
    for d in days:
        i = ks_i[d]; px = ks.iloc[i]
        f = {n: (ks.iloc[i + n] / px - 1) * 100 if i + n < len(ks) else np.nan for n in (20, 60, 120)}
        fut = ks.iloc[i + 1:i + 61]
        mae = (fut.min() / px - 1) * 100 if len(fut) else np.nan
        w = ks.iloc[max(0, i - 120):i + 1]
        rows.append({"d": d, **{f"r{n}": f[n] for n in (20, 60, 120)}, "mae": mae,
                     "abv": (px / w.min() - 1) * 100, "lag": i - ks.index.get_loc(w.idxmin())})
    return pd.DataFrame(rows)

def line(nm, df):
    if df.empty: return f"{nm:<48} 0회"
    g = lambda c: f"{df[c].mean():+6.1f}% {int((df[c] > 0).sum())}/{int(df[c].notna().sum())}"
    return (f"{nm:<48}{len(df):>3}회 | 20일 {g('r20')} | 60일 {g('r60')} | 120일 {g('r120')}"
            f" | 추가하락 {df['mae'].mean():+5.1f}% (최악 {df['mae'].min():+5.1f}) | 저점+{df['abv'].median():.0f}% · {df['lag'].median():.0f}일 뒤")


ma_ok = k >= k.rolling(20).mean()
base = {n: (ks.shift(-n) / ks - 1).loc["2010":].dropna() * 100 for n in (20, 60, 120)}
print("기준(2010~ 아무 날): 60일 {:+.1f}% {:.0%} · 2010~2018 {:+.1f}% · 2019~ {:+.1f}%".format(
    base[60].mean(), (base[60] > 0).mean(), base[60].loc[:"2018"].mean(), base[60].loc["2019":].mean()))
def short(df):
    if df.empty: return "0회"
    return f"{len(df)}회 60일 {df['r60'].mean():+5.1f}% {int((df['r60'] > 0).sum())}/{int(df['r60'].notna().sum())}"
print(f"{'규칙':<30}{'가격':<4}| {'전체':<70}| {'2010~18':<22}| {'2019~26':<22}| 2026 신호")
for nm, st in R.items():
    for tag, s2 in (("없음", st), ("M", combo(st, ma_ok)), ("P", combo(st))):
        a = stats(signals(s2)); l = stats(signals(s2.loc[:"2018"])); c = stats(signals(s2.loc["2019":]))
        full = short(a) + (f" · 20일 {int((a['r20'] > 0).sum())}/{int(a['r20'].notna().sum())} · 최악 {a['mae'].min():+5.1f} · 저점 뒤 {a['lag'].median():.0f}일" if len(a) else "")
        y26 = ", ".join(f"{d:%m.%d}({r:+.0f})" for d, r in zip(a["d"], a["r60"]) if d.year == 2026) if len(a) else ""
        print(f"{nm:<30}{tag:<4}| {full:<70}| {short(l):<22}| {short(c):<22}| {y26}")
