"""새 VKOSPI 규칙(market_report.vk_rule) 확인(2026-11-23): 켜진 날이 백테스트(vkrules 3 기울기 +P) 신호일과 같은지 + 오늘 상태"""
import FinanceDataReader as fdr, market_report as m, vkospi
kc = fdr.DataReader("KS11", "2009-01-01")["Close"].dropna()
r = m.vk_rule(vkospi.series(), kc)
conf = r.index[(r["stage"] == 3) & (r["stage"].shift(1) != 3)]
print("켜진 날:", ", ".join(f"{d:%y.%m.%d}" for d in conf))
print("백테스트: 10.06.22, 11.09.20, 11.10.24, 19.04.29, 20.04.16, 20.06.01, 21.01.27, 24.09.02, 24.10.16, 25.05.09, 25.11.17, 25.12.22, 26.02.11, 26.04.27")
print("2025-01~ 켜진 날 수", int(r.loc["2025":, "on"].sum()), "· 단계별", r.loc["2025":, "stage"].value_counts().to_dict())
vk = m.vkospi_info(kc)
print({k: v for k, v in vk.items() if k not in ("chart", "hist")})
print(m.vk_text(vk))
