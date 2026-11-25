"""VKOSPI로 고점(위험) 신호를 만들 수 있나(2026-11-25 사용자) — 가설 4개 백테스트. 실행 전 사용자와 상의.
신호 = 조건이 처음 켜진 날(전날 꺼짐), 겹침 막기 20거래일. 기간 = VKOSPI 있는 2009-04 ~ (판정·통계는 2010~).
측정: 신호일 종가 기준 20·60·120일 뒤 수익, 60일 뒤 하락 비율, 60일 안 -10% 이상 하락 확률(위험 지표 검증 때 쓴 기준), 60일 안 최대 하락.
비교 기준: 아무 날 / 지금 위험 지표의 '200일 이격 150↑'·'RSI 70↑'(같은 방식으로 신호화)
H1 안주: VKOSPI가 최근 250일 중 하위 q% + 코스피 52주 고점 -3% 이내
H2 동반 상승: 코스피 20일 최고 종가 + VKOSPI가 20일 평균×a 이상(오를 때 불안도 같이 커짐)
H3 바닥 반등: VKOSPI가 60일 최저보다 +b% 이상 + 그 최저가 최근 20일 안 + 코스피 52주 고점 -5% 이내
H4 과열 + 불안 시작: 코스피 200일 이격 ≥ c + VKOSPI 5일 변화 3일 연속 +(바닥 '꺾임'의 반대)"""

import numpy as np, pandas as pd, FinanceDataReader as fdr
import vkospi

vk = vkospi.series()
ks = fdr.DataReader("KS11", "2008-01-01")["Close"].dropna()
vk = vk[vk.index.isin(ks.index)]
k = ks.reindex(vk.index)
ks_i = {d: i for i, d in enumerate(ks.index)}
COOL, FROM = 20, "2010-01-01"

hi252 = ks.rolling(252, min_periods=200).max().reindex(vk.index)
near_hi = lambda p: k >= hi252 * (1 - p / 100)
ma200 = ks.rolling(200).mean().reindex(vk.index)
disp200 = k / ma200 * 100
rsi = (lambda d: 100 - 100 / (1 + d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean() / (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()))(ks.diff()).reindex(vk.index)
vma20 = vk.rolling(20).mean()
vq = lambda q: vk.rolling(250, min_periods=200).quantile(q / 100)
k20hi = k >= k.rolling(20).max()
vlo60 = vk.rolling(60, min_periods=40).min()
lo_pos = vk.rolling(60, min_periods=40).apply(lambda x: len(x) - 1 - int(np.argmin(x)), raw=True)   # 60일 최저가 며칠 전인가
pos3 = (vk.diff(5) > 0).astype(int).rolling(3).min().fillna(0).astype(bool)

V = {
    "H1 안주 q10 (하위 10% + 고점 -3%)": (vk <= vq(10)) & near_hi(3),
    "H1 안주 q5": (vk <= vq(5)) & near_hi(3),
    "H1 안주 q20": (vk <= vq(20)) & near_hi(3),
    "H2 동반 상승 ×1.10": k20hi & (vk >= vma20 * 1.10),
    "H2 동반 상승 ×1.15": k20hi & (vk >= vma20 * 1.15),
    "H2 동반 상승 ×1.25": k20hi & (vk >= vma20 * 1.25),
    "H3 바닥 반등 +20%": (vk >= vlo60 * 1.20) & (lo_pos <= 20) & near_hi(5),
    "H3 바닥 반등 +30%": (vk >= vlo60 * 1.30) & (lo_pos <= 20) & near_hi(5),
    "H4 과열 115 + 불안 시작": (disp200 >= 115) & pos3,
    "H4 과열 120 + 불안 시작": (disp200 >= 120) & pos3,
    "참고: 200일 이격 150↑(지금 위험 항목)": disp200 >= 150,
    "참고: 200일 이격 120↑": disp200 >= 120,
    "참고: RSI 70↑(지금 위험 항목)": rsi >= 70,
}


def edge(st):
    st = st.fillna(False).astype(bool)
    return st & ~st.shift(1, fill_value=False)


def signals(st):
    out, last = [], None
    for d in st[st].index:
        if d < pd.Timestamp(FROM):
            continue
        i = ks_i[d]
        if last is not None and i - last < COOL:
            continue
        out.append(d); last = i
    return out


def stats(days):
    rows = []
    for d in days:
        i = ks_i[d]; px = ks.iloc[i]
        f = {n: (ks.iloc[i + n] / px - 1) * 100 if i + n < len(ks) else np.nan for n in (20, 60, 120)}
        fut = ks.iloc[i + 1:i + 61]
        mdd = (fut.min() / px - 1) * 100 if len(fut) else np.nan
        rows.append({"d": d, **{f"r{n}": f[n] for n in (20, 60, 120)}, "mdd": mdd, "d10": (mdd <= -10) if len(fut) >= 60 else np.nan})
    return pd.DataFrame(rows)


def line(df):
    if df.empty:
        return "0회"
    full = df.dropna(subset=["r60"])
    p = lambda c: f"{df[c].mean():+5.1f}%"
    return (f"{len(df):>3}회 | 20일 {p('r20')} | 60일 {p('r60')} 하락 {int((full['r60'] < 0).sum())}/{len(full)} | 120일 {p('r120')} | "
            f"60일 안 -10% {df['d10'].dropna().mean() * 100:4.0f}% · 최대 하락 평균 {df['mdd'].mean():+5.1f}%")


# 기준: 아무 날(2010~)
idx = ks.loc[FROM:].index
base = stats([d for d in idx if ks_i[d] + 60 < len(ks)][::1])
print(f"VKOSPI {vk.index[0]:%Y-%m-%d} ~ {vk.index[-1]:%Y-%m-%d} · 코스피 ~ {ks.index[-1]:%Y-%m-%d} · 판정 {FROM}~ · 겹침 막기 {COOL}일")
print(f"기준(아무 날) | 20일 {base['r20'].mean():+.1f}% | 60일 {base['r60'].mean():+.1f}% 하락 {(base['r60'] < 0).mean() * 100:.0f}% | "
      f"120일 {base['r120'].mean():+.1f}% | 60일 안 -10% {base['d10'].mean() * 100:.0f}% · 최대 하락 평균 {base['mdd'].mean():+.1f}%")
print()
res = {}
for nm, st in V.items():
    sg = signals(edge(st)); a = stats(sg); res[nm] = a
    print(f"{nm:<34}{line(a)}")
    print(f"{'':<34}2010~2018 {line(a[a['d'] < pd.Timestamp('2019-01-01')]) if not a.empty else ''}")
    print(f"{'':<34}2019~     {line(a[a['d'] >= pd.Timestamp('2019-01-01')]) if not a.empty else ''}")
print()
print("2024~ 신호(날짜 · 60일 뒤 · 60일 안 최대 하락)")
for nm, a in res.items():
    if a.empty:
        continue
    s = ", ".join(f"{r.d:%y.%m.%d}({r.r60:+.0f}/{r.mdd:+.0f})" if pd.notna(r.r60) else f"{r.d:%y.%m.%d}(-/{r.mdd:+.0f})" for r in a.itertuples() if r.d.year >= 2024)
    print(f"  {nm:<34}: {s}")
print()
print("지금 상태:", {nm: bool(st.fillna(False).iloc[-1]) for nm, st in V.items()},
      f"· VKOSPI {vk.iloc[-1]:.1f} · 250일 하위10% {vq(10).iloc[-1]:.1f} · 200일 이격 {disp200.iloc[-1]:.0f}")
