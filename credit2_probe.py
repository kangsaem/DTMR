"""신용잔고 위험 항목: 예탁금 대비 → 시가총액 대비로 바꾸면 나은가(2026-11-25 사용자)
신용 자료(금융투자협회 freesis)를 최대 25년치 요청(1년씩, 없으면 멈춤). 시가총액 = FDR KS11·KQ11 MarCap.
C1 코스피 신용잔고 / 코스피 시총 · C2 전체 신용 / (코스피+코스닥 시총) · C3 코스피 신용잔고 1년(250일) 증가율 · 참고 지금(전체 신용 / 예탁금)
각각 '그날까지 5년 중 백분위 ≥ 90'(지금 항목과 같은 방식). 측정 = riskaudit_probe와 같음."""
import functools, numpy as np, pandas as pd, FinanceDataReader as fdr
import market_report as m

m._freesis_rows = functools.partial(m._freesis_rows, years=25)
cred, dep = m.credit_tables()
print(f"신용 {cred.index[0]:%Y-%m-%d} ~ {cred.index[-1]:%Y-%m-%d} ({len(cred)}일) · 예탁금 {'실패 ' + str(dep)[:80] if isinstance(dep, Exception) else f'{dep.index[0]:%Y-%m-%d}~ ({len(dep)}일)'}")

kd = fdr.DataReader("KS11", "1998-01-01"); qd = fdr.DataReader("KQ11", "1998-01-01")
ks = kd["Close"].dropna(); I = ks.index; n = len(ks); c = ks.values
fwd60 = pd.Series([(c[i + 60] / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
dd60 = pd.Series([(c[i + 1:i + 61].min() / c[i] - 1) * 100 if i + 60 < n else np.nan for i in range(n)], index=I)
mk = pd.to_numeric(kd["MarCap"], errors="coerce"); mq = pd.to_numeric(qd["MarCap"], errors="coerce").reindex(mk.index, method="ffill")
unit = 1e8 if mk.dropna().median() > 1e12 else 1     # 원 → 억원
print(f"시총 단위 {'원' if unit == 1e8 else '억원?'} · 코스피 시총 지금 {mk.iloc[-1] / unit / 1e4:,.0f}조")

cr = cred.reindex(I, method="ffill", limit=5)
C1 = cr["cred_ks"] / (mk.reindex(I) / unit) * 100
C2 = cr["cred"] / ((mk + mq).reindex(I) / unit) * 100
C3 = (cr["cred_ks"] / cr["cred_ks"].shift(250) - 1) * 100
CUR = (cr["cred"] / dep.reindex(I, method="ffill", limit=5) * 100) if not isinstance(dep, Exception) else pd.Series(np.nan, index=I)

def pct5(s):   # 그날까지 최대 5년(1250일) 중 백분위, 250일 이상 쌓인 뒤부터
    return s.rolling(1250, min_periods=250).apply(lambda x: (x[~np.isnan(x)] <= x[-1]).mean() * 100 if not np.isnan(x[-1]) else np.nan, raw=True)

V = {}
for nm, s in (("C1 코스피 신용/코스피 시총", C1), ("C2 전체 신용/전체 시총", C2), ("C3 코스피 신용 1년 증가율", C3), ("참고: 지금 신용/예탁금", CUR)):
    p = pct5(s)
    V[nm + " 상위 10%"] = (p >= 90).where(p.notna())
    V[nm + " 상위 20%"] = (p >= 80).where(p.notna())
    print(f"{nm}: 지금 {s.iloc[-1]:.3f} (5년 중 {p.iloc[-1]:.0f}%) · 최고 {s.max():.3f}({s.idxmax():%y.%m.%d}) · 2026-06-22(코스피 최고점) {s.get(pd.Timestamp('2026-06-22'), np.nan):.3f} (5년 중 {p.get(pd.Timestamp('2026-06-22'), np.nan):.0f}%)")

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
    if valid.sum() == 0: return f"{nm:<30} 자료 없음"
    if o.sum() == 0: return f"{nm:<30} 0일(자료 {int(valid.sum())}일, {valid[valid].index[0]:%Y}~)"
    fv, dd = fwd60.loc[since:][o], dd60.loc[since:][o]
    rr = runs(on.values); ix = on.index; first = [ix[a] for a, b in rr if pd.notna(fwd60.get(ix[a]))]
    p10, b10 = (dd <= -10).mean() * 100, (bd <= -10).mean() * 100
    return (f"{nm:<30} {len(rr):>3}구간 {int(o.sum()):>4}일({o.sum() / valid.sum() * 100:4.1f}%, 자료 {valid[valid].index[0]:%Y}~) | 날: 60일 {fv.mean():+5.1f}% · -10%↓ {p10:3.0f}%(기준 {b10:.0f}%, ×{p10 / b10:.1f}) · 최대하락 {dd.mean():+5.1f}%"
            f" | 첫날 -10%↓ {(dd60.reindex(first) <= -10).mean() * 100:3.0f}% | 구간 {', '.join(f'{ix[a]:%y.%m}' for a, b in rr[-6:])}")

for since in ("2000-01-01", "2010-01-01"):
    print(f"\n===== {since[:4]}~")
    for k, v in V.items(): print(row(k, v, since))
