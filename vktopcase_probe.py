"""코스피 큰 고점 전후 VKOSPI 모습(2026-11-25, 고점 가설 좁히기): 2026 역사상 최고점 + 과거 큰 고점(고점 뒤 6개월 안 -20% 이상 하락)"""
import numpy as np, pandas as pd, FinanceDataReader as fdr
import vkospi
vk = vkospi.series(); ks = fdr.DataReader("KS11", "2008-01-01")["Close"].dropna()
vk = vk.reindex(ks.index).ffill(limit=2)
vma = vk.rolling(20).mean(); vq = vk.rolling(250, min_periods=200).apply(lambda x: (x[-1] >= x).mean() * 100, raw=True)
d200 = ks / ks.rolling(200).mean() * 100
# 큰 고점: 그날이 앞뒤 120거래일 최고 + 이후 126일 안 -20% 이상
tops = []
for i in range(250, len(ks) - 5):
    w = ks.iloc[max(0, i - 120):i + 121]
    if ks.iloc[i] == w.max():
        fut = ks.iloc[i + 1:i + 127]
        if len(fut) and fut.min() / ks.iloc[i] - 1 <= -0.15:
            tops.append(ks.index[i])
ath = ks.idxmax(); tops = sorted(set(tops + [ath]))
print(f"역사상 최고점 {ath:%Y-%m-%d} {ks.max():,.0f} · 지금 {ks.index[-1]:%Y-%m-%d} {ks.iloc[-1]:,.0f} ({(ks.iloc[-1] / ks.max() - 1) * 100:+.0f}%)")
print("큰 고점(앞뒤 120일 최고 + 6개월 안 -15%↓) — 고점 기준 -40·-20·-10·-5·0·+5·+10·+20거래일의 VKOSPI / 20일 평균 대비 / 1년 중 백분위 / 200일 이격")
for t in tops:
    i = ks.index.get_loc(t); fut = ks.iloc[i + 1:i + 127]
    print(f"\n■ {t:%Y-%m-%d} 코스피 {ks.iloc[i]:,.0f} → 6개월 안 최저 {(fut.min() / ks.iloc[i] - 1) * 100:+.0f}%")
    for o in (-40, -20, -10, -5, 0, 5, 10, 20):
        j = i + o
        if 0 <= j < len(ks) and pd.notna(vk.iloc[j]):
            print(f"   {o:+4d}일 {ks.index[j]:%y.%m.%d} VKOSPI {vk.iloc[j]:5.1f} · 20일평균 대비 {vk.iloc[j] / vma.iloc[j]:4.2f}배 · 1년 백분위 {vq.iloc[j]:3.0f} · 이격 {d200.iloc[j]:4.0f} · 코스피 {ks.iloc[j]:,.0f}")
