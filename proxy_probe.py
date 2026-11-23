"""프록시 배포 확인(2026-11-23): 배당용 네이버 /api/stock/ 경로가 moneypie-proxy를 통과하는지"""
import json, urllib.request, urllib.parse
P = "https://moneypie-proxy.y0n2.workers.dev/?url="
H = {"User-Agent": "Mozilla/5.0", "Origin": "https://www.moneypie.kr"}
for c in ["005930", "069500"]:
    u = P + urllib.parse.quote(f"https://m.stock.naver.com/api/stock/{c}/integration", safe="")
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20)
        j = json.loads(r.read())
        ti = {x.get("code"): x.get("value") for x in j.get("totalInfos") or []}
        print(c, r.status, "배당", ti.get("dividendYieldRatio"), "ETF", (j.get("etfKeyIndicator") or {}).get("dividendYieldTtm"))
    except Exception as e:
        print(c, "실패", e)
