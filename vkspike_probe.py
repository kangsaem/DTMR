"""VKOSPI 급등 조건 확인(2026-11-23, 사용자 '왜 급등 기준을 넘어야 하나'): 급등 조건만 바꾸고 나머지는 지금 규칙과 같게
꺾임 = 5일 변화 3일 연속 − + 20일 평균 아래 / 가격 P = 20거래일 안에 '20일 신저점 없음 + 20일선 위' 첫날(안 맞으면 버림) / 쿨다운 20일
비교: 지금(60일 최고 ≥30 + 20일 최고 ≥ 120일 중간값×1.5) · 급등 조건 없음 · 고정 기준만(60일 최고 ≥30/40/50) · 상대 기준만(×1.2/1.5)"""

import numpy as np, pandas as pd, FinanceDataReader as fdr
import vkospi

vk = vkospi.series()
ks = fdr.DataReader("KS11", "2009-01-01")["Close"].dropna()
vk = vk[vk.index.isin(ks.index)]
k = ks.reindex(vk.index)
ks_i = {d: i for i, d in enumerate(ks.index)}
COOL = 20

ma20 = vk.rolling(20).mean()
mx60 = vk.rolling(60, min_periods=20).max()
mx20 = vk.rolling(20).max()
med120 = vk.rolling(120, min_periods=60).median()
neg = (vk.diff(5) < 0).astype(int).rolling(3).min().fillna(0).astype(bool)
below = vk < ma20
price_ok = ((k.rolling(20).apply(lambda x: np.argmin(x) == 0, raw=True) == 1) & (k >= k.rolling(20).mean())).fillna(False)

def edge(st):
    st = st.fillna(False).astype(bool)
    return st & ~st.shift(1, fill_value=False)

T = pd.Series(True, index=vk.index)
SP = {
    "지금: ≥30 + 중간값×1.5": (mx60 >= 30) & (mx20 >= med120 * 1.5),
    "급등 조건 없음": T,
    "고정만: 60일 최고 ≥30": mx60 >= 30,
    "고정만: 60일 최고 ≥40": mx60 >= 40,
    "고정만: 60일 최고 ≥50": mx60 >= 50,
    "상대만: 중간값×1.2": mx20 >= med120 * 1.2,
    "상대만: 중간값×1.5": mx20 >= med120 * 1.5,
}

def combo(st):
    out = pd.Series(False, index=st.index); idx = list(st.index)
    for d in st[st].index:
        i = idx.index(d)
        for j in range(i, min(i + 21, len(idx))):
            if price_ok.iloc[j]: out.iloc[j] = True; break
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
        rows.append({"d": d, **{f"r{n}": f[n] for n in (20, 60, 120)}, "mae": (fut.min() / px - 1) * 100 if len(fut) else np.nan})
    return pd.DataFrame(rows)

def short(df):
    if df.empty: return "0회"
    return f"{len(df)}회 60일 {df['r60'].mean():+5.1f}% {int((df['r60'] > 0).sum())}/{int(df['r60'].notna().sum())}"

base = {n: (ks.shift(-n) / ks - 1).loc["2010":].dropna() * 100 for n in (20, 60, 120)}
print("기준(2010~ 아무 날): 60일 {:+.1f}% {:.0%} · 2010~2018 {:+.1f}% · 2019~ {:+.1f}%".format(
    base[60].mean(), (base[60] > 0).mean(), base[60].loc[:"2018"].mean(), base[60].loc["2019":].mean()))
print(f"VKOSPI {vk.index[0]:%Y-%m-%d} ~ {vk.index[-1]:%Y-%m-%d} · 6개월 중간값 지금 {med120.iloc[-1]:.1f} → ×1.5 = {med120.iloc[-1]*1.5:.1f}, ×1.2 = {med120.iloc[-1]*1.2:.1f} · 60일 최고 {mx60.iloc[-1]:.1f}")
print()
print(f"{'급등 조건':<26}| {'전체':<26}| {'20일':<9}| {'120일':<16}| {'최악 추가하락':<10}| {'2010~18':<22}| {'2019~26':<22}")
detail = {}
for nm, sp in SP.items():
    st = combo(edge(sp.fillna(False) & neg & below))
    a = stats(signals(st)); l = stats(signals(st.loc[:"2018"])); c = stats(signals(st.loc["2019":]))
    if a.empty:
        print(f"{nm:<26}| 0회"); continue
    g = lambda col: f"{a[col].mean():+5.1f}% {int((a[col] > 0).sum())}/{int(a[col].notna().sum())}"
    print(f"{nm:<26}| {short(a):<26}| {int((a['r20'] > 0).sum())}/{int(a['r20'].notna().sum()):<6}| {g('r120'):<16}| {a['mae'].min():+6.1f}% {a['mae'].mean():+5.1f}% | {short(l):<22}| {short(c):<22}")
    detail[nm] = a
print()
print("2025~ 신호(날짜·60일 뒤)")
for nm, a in detail.items():
    s = ", ".join((f"{d:%y.%m.%d}({r:+.0f}" if pd.notna(r) else f"{d:%y.%m.%d}(지금 {(ks.iloc[-1] / ks.loc[d] - 1) * 100:+.0f}") + f", 최저 {mae:+.0f})" for d, r, mae in zip(a["d"], a["r60"], a["mae"]) if d.year >= 2025)
    w = a.loc[a["mae"].idxmin()]
    s += f"  ← 최악 {w['d']:%y.%m.%d} {w['mae']:+.1f}%"
    print(f"  {nm:<26}: {s}")
