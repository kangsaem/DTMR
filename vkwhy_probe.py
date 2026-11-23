"""VKOSPI 꺾임 뒤 왜 회복(3단계)으로 못 넘어갔나(2026-11-23 사용자): 2026-04 이후 2단계(기다림) 날마다 코스피 조건 두 개"""
import pandas as pd, FinanceDataReader as fdr
import market_report as m, vkospi

vk = vkospi.series()
kc = fdr.DataReader("KS11", "2025-01-01")["Close"].dropna()
r = m.vk_rule(vk, kc)
r = r.loc["2026-04-01":]
print("날짜        단계 대기 | 코스피   20일선  위?  | 20일 최저(날짜)       신저점 뒤 | 둘 다")
for d, t in r.iterrows():
    if t["stage"] < 2 and not (t["stage"] == 0 and r["stage"].shift(1).get(d, 0) >= 2):
        continue
    w = t["k"]; lo = r["k"].loc[:d].tail(20)
    lod = lo.idxmin()
    print(f"{d:%Y-%m-%d}  {int(t['stage'])}   {int(t['wait']):>2}  | {t['k']:>7,.0f} {t['kma']:>7,.0f}  {'O' if t['ma_ok'] else 'X'}   | "
          f"{lo.min():>7,.0f}({lod:%m-%d})  {len(lo.loc[lod:]) - 1:>2}일 {'O' if t['nolow'] else 'X'} | {'O' if t['ma_ok'] and t['nolow'] else ''}")
