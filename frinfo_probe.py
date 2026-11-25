"""foreign_info 실제 자료 확인(2026-11-25): 외국인 자료 채우기 + 판정 + 기록"""
import FinanceDataReader as fdr, market_report as m, foreign
ks = fdr.DataReader("KS11", m.START)["Close"].dropna()
print("받기:", foreign.update(limit_min=5))
fr = m.foreign_info(ks)
print({k: v for k, v in fr.items() if k != "hist"})
h = fr["hist"]; print("기록", h["d"][0], "~", h["d"][-1], len(h["d"]), "일 · 켜진 날", h["on"].count("1"))
on = h["on"]; runs = []; i = 0
while i < len(on):
    if on[i] == "1":
        j = i
        while j + 1 < len(on) and on[j + 1] == "1": j += 1
        runs.append((h["d"][i], h["d"][j], j - i + 1)); i = j + 1
    else: i += 1
print("켜진 구간:", runs)
print("최근 5일 20일 누적(억):", list(zip(h["d"][-5:], h["f20"][-5:])))
