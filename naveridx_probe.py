"""네이버로 코스피·나스닥·S&P 일별 종가 받기 확인(2026-11-25, 앱 월별 탭 야후 빈 값 대안) — 직접 + 앱 프록시 경유"""
import requests, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126", "Referer": "https://m.stock.naver.com/"}
PX = "https://moneypie-proxy.y0n2.workers.dev/?url="
C = [
 "https://m.stock.naver.com/api/index/KOSPI/price?pageSize=5&page=1",
 "https://api.stock.naver.com/index/KOSPI/price?pageSize=5&page=1",
 "https://api.stock.naver.com/index/.IXIC/price?pageSize=5&page=1",
 "https://api.stock.naver.com/index/.INX/price?pageSize=5&page=1",
 "https://m.stock.naver.com/api/index/.IXIC/price?pageSize=5&page=1",
 "https://api.stock.naver.com/chart/domestic/index/KOSPI?periodType=dayCandle&count=5",
 "https://api.stock.naver.com/chart/foreign/index/.IXIC?periodType=dayCandle&count=5",
 "https://api.stock.naver.com/chart/foreign/index/.INX?periodType=dayCandle&count=5",
 "https://api.finance.naver.com/siseJson.naver?symbol=KOSPI&requestType=1&startTime=20261117&endTime=20261125&timeframe=day",
 "https://api.stock.naver.com/index/KOSPI/price?pageSize=60&page=30",
 "https://api.stock.naver.com/index/.IXIC/price?pageSize=60&page=30",
]
for u in C:
    for via in ("직접", "프록시"):
        try:
            r = requests.get(u if via == "직접" else PX + urllib.parse.quote(u, safe=""), headers=UA, timeout=20)
            t = r.text.replace("\n", " ")
            print(f"[{via}] {r.status_code} {u}\n    {t[:330]}")
        except Exception as e:
            print(f"[{via}] 실패 {u} {e}")
