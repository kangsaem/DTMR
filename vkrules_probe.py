"""VKOSPI 바닥 신호 규칙 비교(2026-11-23, 사용자 'ㄱㄱ')
신호일 = 규칙이 꺼짐→켜짐으로 바뀐 날, 앞 신호 뒤 20거래일 안의 신호는 버림(쿨다운).
지표: 횟수 · 20/60/120거래일 뒤 코스피 수익률 평균·플러스 비율 · 60일 안 최대 추가 하락 · 늦음(120일 저점 대비 %, 저점 뒤 거래일)
기간 나눔: 학습 2010~2018 / 확인 2019~2026. 조합(+P) = 신호 뒤 20거래일 안에 '코스피 20거래일 신저점 없음 + 종가 ≥ 20일선'이 처음 맞는 날(안 맞으면 버림)."""
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
R["0 지금: 30↓ + 60일 안 30↑"] = edge(m.vkospi_on(vk).astype(bool))
for X in (30, 35, 40):                          # 1. 단계 하향 돌파: 직전 60일 최고가 X의 1.3배 이상이었고 오늘 X 아래로
    R[f"1 {X} 하향 돌파(60일 최고 ≥{X * 1.3:.0f})"] = (vk < X) & (vk.shift(1) >= X) & (mx60.shift(1) >= X * 1.3)
for p in (30, 40):                              # 2. 60일 최고 대비 -p% (최고 ≥30)
    R[f"2 60일 최고 대비 -{p}%"] = edge((vk <= mx60 * (1 - p / 100)) & (mx60 >= 30))
spike = (mx60 >= 30) & (vk.rolling(20).max() >= vk.rolling(120, min_periods=60).median() * 1.5)
R["3 기울기 반전(급등 뒤 5일 변화 3일 연속 −, 20일선 아래)"] = edge(spike & (vk.diff(5) < 0).rolling(3).min().astype(bool) & (vk < ma20))
up = vk > ma20 + 2 * sd20
R["4 볼린저 상단 넘은 뒤 10일 안 밴드 안 복귀"] = (~up) & up.shift(1, fill_value=False) & (mx60 >= 25)
R["4b 볼린저 상단 넘은 뒤 20일선 아래로"] = edge((vk < ma20) & up.rolling(15).max().astype(bool) & (mx60 >= 25))

low20 = k.rolling(20).min()
price_ok = (k.rolling(20).apply(lambda x: np.argmin(x) == 0, raw=True) == 1) & (k >= k.rolling(20).mean())   # 20일 안 신저점 없음(최저가 20일 전 첫날) + 20일선 위

def combo(st):   # 신호 뒤 20거래일 안에 가격 조건이 처음 맞는 날로 미룸(안 맞으면 버림)
    out = pd.Series(False, index=st.index); ok = price_ok.reindex(st.index).fillna(False).astype(bool)
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

base = {n: (ks.shift(-n) / ks - 1).loc["2010":].dropna() * 100 for n in (20, 60, 120)}
print("기준(2010~ 아무 날): 20일 {:+.1f}% {:.0%} | 60일 {:+.1f}% {:.0%} | 120일 {:+.1f}% {:.0%}".format(
    base[20].mean(), (base[20] > 0).mean(), base[60].mean(), (base[60] > 0).mean(), base[120].mean(), (base[120] > 0).mean()))
print("2019~ 기준: 60일 {:+.1f}% {:.0%}".format(base[60].loc["2019":].mean(), (base[60].loc["2019":] > 0).mean()))
res = {}
for per, (a, b) in (("전체 2010~2026", ("2010", "2026")), ("학습 2010~2018", ("2010", "2018")), ("확인 2019~2026", ("2019", "2026"))):
    print(f"\n===== {per}")
    for nm, st in R.items():
        for tag, s2 in (("", st), (" +P", combo(st))):
            df = stats(signals(s2.loc[a:b]))
            print(line(nm + tag, df)); res[(per, nm + tag)] = df
print("\n===== 신호 날짜(전체)")
for nm in R:
    for tag in ("", " +P"):
        df = res[("전체 2010~2026", nm + tag)]
        print(f"{nm + tag}: " + ", ".join(f"{d:%y.%m.%d}({r:+.0f})" for d, r in zip(df.get('d', []), df.get('r60', []))))
