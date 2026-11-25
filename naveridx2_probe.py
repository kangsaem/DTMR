"""네이버 지수 일별 — 앱 프록시를 앱 주소(Origin)로 경유 + 기간 지정 확인(2026-11-25)"""
import requests, urllib.parse, json
PX = "https://moneypie-proxy.y0n2.workers.dev/?url="
for org in ("https://kangsaem.github.io",):
    H = {"User-Agent": "Mozilla/5.0 Chrome/126", "Origin": org, "Referer": org + "/moneypiee/"}
    for u in ["https://api.finance.naver.com/siseJson.naver?symbol=KOSPI&requestType=1&startTime=20261117&endTime=20261125&timeframe=day",
              "https://api.stock.naver.com/chart/foreign/index/.IXIC?periodType=dayCandle&startDateTime=202611170000&endDateTime=202611252359",
              "https://api.stock.naver.com/chart/foreign/index/.INX?periodType=dayCandle&startDateTime=202605010000&endDateTime=202611252359",
              "https://api.stock.naver.com/chart/domestic/index/KOSPI?periodType=dayCandle&startDateTime=202001010000&endDateTime=202611252359"]:
        try:
            r = requests.get(PX + urllib.parse.quote(u, safe=""), headers=H, timeout=25); t = r.text
            info = ""
            if t.lstrip().startswith("{"):
                p = json.loads(t).get("priceInfos") or []
                info = f"→ {len(p)}일 {p[0]['localDate'] if p else ''}~{p[-1]['localDate'] if p else ''} 마지막 {p[-1]['closePrice'] if p else ''}"
            print(f"[{org}] {r.status_code} {u[:110]}\n    {info or t[:200].replace(chr(10), ' ')}")
        except Exception as e:
            print("실패", u, e)
