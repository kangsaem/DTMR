"""(lo2y) '시작 뒤 2년 안 저점이 시작일 지수보다 아래'의 아무 날 기준 확률(2026-11-25, riskmix 맞음 기준 비교용)."""
import FinanceDataReader as fdr, numpy as np, pandas as pd
ks = fdr.DataReader("KS11", "1997-01-01")["Close"].dropna(); c = ks.values; n = len(c)
lo = pd.Series([c[i+1:i+501].min()/c[i]*100-100 if i+500 < n else np.nan for i in range(n)], index=ks.index)
for a, b in [("1999","2024"),("1999","2009"),("2010","2020"),("2021","2024")]:
    s = lo[a:b].dropna(); print(f"{a}~{b}: 아무 날 2년 안 저점 < 그날 {(s<0).mean()*100:.0f}% · -10% 아래 {(s<-10).mean()*100:.0f}% · -20% 아래 {(s<-20).mean()*100:.0f}%")
