"""배당수익률 2단계 확인(2026-11-23): 네이버 종목·ETF 정보에서 배당수익률이 어디에 어떤 형식으로 오는지"""
import json, urllib.request
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}
def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20).read())

def find(o, path=""):
    """'divid'·'배당'이 들어간 키·값을 모두 출력"""
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}.{k}"
            if "divid" in k.lower() or "배당" in str(k):
                print("   KEY", p, "=", json.dumps(v, ensure_ascii=False)[:200])
            find(v, p)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, dict) and any("divid" in str(x).lower() or "배당" in str(x) for x in v.values()):
                print("   ITEM", f"{path}[{i}]", json.dumps(v, ensure_ascii=False)[:200])
            find(v, f"{path}[{i}]")

# 삼성전자(배당), 맥쿼리인프라(고배당), 에코프로비엠(무배당 가능), KODEX 200·TIGER 미국배당다우존스(ETF), KODEX 레버리지(분배 없음 가능)
CODES = ["005930", "088980", "247540", "069500", "458730", "122630"]
URLS = [
    "https://m.stock.naver.com/api/stock/{c}/integration",
    "https://m.stock.naver.com/api/stock/{c}/basic",
    "https://m.stock.naver.com/api/stock/{c}/etfAnalysis",
    "https://polling.finance.naver.com/api/realtime/domestic/stock/{c}",
]
for c in CODES:
    print("=" * 10, c)
    for u in URLS:
        url = u.format(c=c)
        try:
            j = get(url)
            print(" OK", url, "| 최상위 키:", list(j.keys())[:25] if isinstance(j, dict) else type(j).__name__)
            find(j)
        except Exception as e:
            print(" 실패", url, e)
