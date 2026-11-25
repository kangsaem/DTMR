"""외국인 순매수로 위험 지표를 만들 수 있나(2026-11-25 사용자 A) — riskaudit_probe와 같은 기준(켜진 날 60일 안 -10% 하락 확률 등)
자료: results/foreign_kospi.json(네이버 KOSPI trend, 억원, 1999~) + 빠진 날은 이번에 받음(저장은 안 함).
금액은 시장 크기가 30년 새 수십 배라 그대로 비교 못 함 → '최근 250거래일 중 백분위'로 봄. 코스피 거래대금(FDR Amount)이 있으면 비율판도.
F1 대규모 이탈: 20일 누적 순매수가 최근 1년 중 하위 10%(5%도)
F2 엇갈림: 코스피 20일 +5%↑인데 외국인 20일 누적 순매도(고점 -3% 이내판도)
F3 매도 지속: 60일 누적 순매수가 최근 1년 중 하위 10%
참고: 반대(20일 누적 상위 10% = 대량 매수)"""
import json, time, numpy as np, pandas as pd, requests, FinanceDataReader as fdr
from concurrent.futures import ThreadPoolExecutor
import market_report as m

ks_df = fdr.DataReader("KS11", "1998-01-01"); ks = ks_df["Close"].dropna(); I = ks.index; n = len(ks); c = ks.values
print("코스피 열:", list(ks_df.columns))
fwd60 = pd.Series([(c[i + 60] / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
dd60 = pd.Series([(c[i + 1:i + 61].min() / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)

have = json.load(open("results/foreign_kospi.json"))
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}
need = [d.strftime("%Y%m%d") for d in I if d >= pd.Timestamp("2026-10-15") and d.strftime("%Y%m%d") not in have]
def one(d):
    for k in range(3):
        try:
            j = requests.get(f"https://m.stock.naver.com/api/index/KOSPI/trend?bizdate={d}", headers=H, timeout=15).json()
            return d, (float(str(j["foreignValue"]).replace(",", "").replace("+", "")) if j.get("bizdate") == d else None)
        except Exception:
            time.sleep(1 + k)
    return d, None
with ThreadPoolExecutor(6) as ex:
    for d, v in ex.map(one, need):
        if v is not None: have[d] = v
f = pd.Series({pd.Timestamp(k): v for k, v in have.items()}).sort_index()
F0 = f[f != 0].index[0]; f = f[f.index >= F0].reindex(I); f[f.index >= F0] = f[f.index >= F0].fillna(0)   # 2005 전 = 자료 없음(NaN)
print(f"외국인 순매수 {f[f != 0].index[0]:%Y-%m-%d} ~ {f[f != 0].index[-1]:%Y-%m-%d} · 이번에 새로 {len(need)}일 요청")

f20, f60 = f.rolling(20).sum(), f.rolling(60).sum()
pct = lambda s: s.rolling(250, min_periods=200).apply(lambda x: (x <= x[-1]).mean() * 100, raw=True)
p20, p60 = pct(f20), pct(f60)
k20 = (ks / ks.shift(20) - 1) * 100
near_hi = ks >= ks.rolling(252, min_periods=200).max() * 0.97
V = {
    "F1 20일 누적 하위 10%": p20 <= 10, "F1 20일 누적 하위 5%": p20 <= 5,
    "F2 코스피 20일 +5%↑ & 외국인 20일 매도": (k20 >= 5) & (f20 < 0),
    "F2' 고점 -3% 안 & 외국인 20일 매도": near_hi & (f20 < 0),
    "F3 60일 누적 하위 10%": p60 <= 10,
    "참고: 20일 누적 상위 10%(대량 매수)": p20 >= 90,
}
if "Amount" in ks_df:
    amt = pd.to_numeric(ks_df["Amount"], errors="coerce").reindex(I)
    unit = 1e8 if amt.dropna().median() > 1e10 else 1          # 원 → 억원
    r20 = f20 / (amt / unit).rolling(20).sum() * 100
    print(f"거래대금 자료 {amt.dropna().index[0]:%Y-%m-%d}~ · 외국인 20일 순매수/거래대금 지금 {r20.iloc[-1]:+.2f}% · 하위 5% {r20.quantile(.05):+.2f}% · 상위 5% {r20.quantile(.95):+.2f}%")
    V["F1r 20일 순매수/거래대금 ≤ -3%"] = r20 <= -3
    V["F1r 20일 순매수/거래대금 ≤ -5%"] = r20 <= -5

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

def row(nm, cond, since):
    s = cond.loc[since:]; valid = s.notna() & fwd60.loc[since:].notna(); on = s.fillna(False).astype(bool)
    o = on & valid; bd = dd60.loc[since:][valid]
    if o.sum() == 0: return f"{nm:<34} 0일"
    fv, dd = fwd60.loc[since:][o], dd60.loc[since:][o]
    rr = runs(on.values); ix = on.index; first = [ix[a] for a, b in rr if pd.notna(fwd60.get(ix[a]))]
    p10, b10 = (dd <= -10).mean() * 100, (bd <= -10).mean() * 100
    return (f"{nm:<34} {len(rr):>3}구간 {int(o.sum()):>4}일({o.sum() / valid.sum() * 100:4.1f}%) | 날: 60일 {fv.mean():+5.1f}% · -10%↓ {p10:3.0f}%(×{p10 / b10:.1f}) · 최대하락 {dd.mean():+5.1f}%"
            f" | 첫날: 60일 {fwd60.reindex(first).mean():+5.1f}% · -10%↓ {(dd60.reindex(first) <= -10).mean() * 100:3.0f}% | 최근 {', '.join(f'{ix[a]:%y.%m}' for a, b in rr[-3:])}")

for since in ("2006-01-01", "2010-01-01"):   # 외국인 자료 2005~ + 1년 백분위 준비
    b, bd = fwd60.loc[since:].dropna(), dd60.loc[since:].dropna()
    print(f"\n===== {since[:4]}~ 기준(아무 날) 60일 {b.mean():+.1f}% · -10%↓ {(bd <= -10).mean() * 100:.0f}% · 최대하락 {bd.mean():+.1f}%")
    for k, v in V.items(): print(row(k, v, since))
    print(row("참고: 50일 이격 120↑(지금 위험 항목)", ks / ks.rolling(50).mean() * 100 >= 120, since))

# 이미 하락 중이었나: 켜진 첫날 기준 직전 20일 코스피 변화(늦은 신호인지)
print("\n켜진 첫날 직전 20일 코스피 변화 평균(음수면 '이미 빠지는 중'에 켜짐), 2006~")
for k, v in V.items():
    on = v.fillna(False).astype(bool).loc["2006":]; rr = runs(on.values); ix = on.index
    if rr: print(f"  {k:<34} {np.nanmean([k20.get(ix[a]) for a, b in rr]):+5.1f}%")
print(f"\n지금({I[-1]:%Y-%m-%d}) 외국인 20일 누적 {f20.iloc[-1]:+,.0f}억 (1년 중 {p20.iloc[-1]:.0f}%) · 60일 {f60.iloc[-1]:+,.0f}억 ({p60.iloc[-1]:.0f}%) · 코스피 20일 {k20.iloc[-1]:+.1f}%")
