"""어제(11/24) 코스피가 그래프에 안 나온 원인 확인(2026-11-25): 야후 ^KS11 최근 일봉(앱 월별 탭이 쓰는 주소 그대로) · FDR KS11 · KRX VKOSPI 11/24 올라왔나"""
import json, os, urllib.request, datetime as dt, requests, FinanceDataReader as fdr
UA = {"User-Agent": "Mozilla/5.0"}
for p in ("range=10d&interval=1d",):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?{p}"
    try:
        j = requests.get(u, headers=UA, timeout=20).json()["chart"]["result"][0]; off = j["meta"].get("gmtoffset", 0)
        cl = j["indicators"]["quote"][0]["close"]
        print("야후 ^KS11", [(dt.datetime.utcfromtimestamp(t + off).strftime("%m-%d %H:%M"), None if c is None else round(c, 2)) for t, c in zip(j["timestamp"], cl)])
        print("  meta regularMarketTime", dt.datetime.utcfromtimestamp(j["meta"]["regularMarketTime"] + off), j["meta"].get("regularMarketPrice"))
    except Exception as e:
        print("야후 실패", e)
print("FDR KS11", fdr.DataReader("KS11", "2026-11-17")["Close"].round(2).to_dict())
key = os.environ.get("KRX_API_KEY", "")
for d in ("20261124", "20261125"):
    try:
        req = urllib.request.Request(f"https://data-dbg.krx.co.kr/svc/apis/idx/drvprod_dd_trd?basDd={d}", headers={"AUTH_KEY": key})
        rows = json.load(urllib.request.urlopen(req, timeout=20)).get("OutBlock_1") or []
        v = [r.get("CLSPRC_IDX") for r in rows if "변동성" in r.get("IDX_NM", "")]
        print("KRX VKOSPI", d, "행", len(rows), v, "확인 시각(UTC)", dt.datetime.utcnow().strftime("%H:%M"))
    except Exception as e:
        print("KRX", d, "실패", e)
