"""VKOSPI 출처 확인(2026-11-23): GitHub 서버에서 일별 VKOSPI를 받을 수 있는 곳"""
import json, urllib.request, urllib.parse, traceback
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
def raw(u, data=None, h=None):
    req = urllib.request.Request(u, data=data, headers=h or H)
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
def t(name, f):
    try:
        out = f(); print("OK ", name, "|", str(out)[:400].replace("\n", " "))
    except Exception as e:
        print("실패", name, "|", repr(e)[:200])
# 1) FinanceDataReader
def fdr():
    import FinanceDataReader as F
    for s in ["VKOSPI", "KRX:VKOSPI", "^VKOSPI"]:
        try:
            d = F.DataReader(s, "2026-01-01"); return s, len(d), d.tail(3).to_dict()
        except Exception as e: print("   fdr", s, repr(e)[:120])
    raise RuntimeError("fdr 모두 실패")
t("FDR", fdr)
# 2) 야후
for s in ["^VKOSPI", "^KSVKOSPI", "VKOSPI.KS"]:
    t("yahoo " + s, lambda s=s: raw(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?range=1mo&interval=1d"))
# 3) 네이버
t("naver siseJson VKOSPI", lambda: raw("https://api.finance.naver.com/siseJson.naver?symbol=VKOSPI&requestType=1&startTime=20261001&endTime=20261123&timeframe=day"))
t("naver polling index VKOSPI", lambda: raw("https://polling.finance.naver.com/api/realtime/domestic/index/VKOSPI"))
t("naver m.stock index VKOSPI basic", lambda: raw("https://m.stock.naver.com/api/index/VKOSPI/basic"))
t("naver m.stock index VKOSPI price", lambda: raw("https://m.stock.naver.com/api/index/VKOSPI/price?pageSize=10&page=1"))
t("naver sise_index VKOSPI(html)", lambda: raw("https://finance.naver.com/sise/sise_index_day.naver?code=VKOSPI")[:3000].split("<table")[1][:600] if "<table" in raw("https://finance.naver.com/sise/sise_index_day.naver?code=VKOSPI") else "표 없음")
# 4) KRX 정보데이터시스템 (파생지수 시세)
def krx():
    import urllib.parse as up
    h = dict(H); h.update({"Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    form = {"bld": "dbms/MDC/STAT/standard/MDCSTAT01201", "locale": "ko_KR", "indIdx": "1", "indIdx2": "300", "codeNmindIdx_finder_drvetcidx0_1": "코스피 200 변동성지수",
            "strtDd": "20261001", "endDd": "20261120", "share": "2", "money": "3", "csvxls_isNo": "false"}
    return raw("http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd", up.urlencode(form).encode(), h)
t("KRX getJsonData", krx)
# 5) investing 대체: stooq
t("stooq vkospi", lambda: raw("https://stooq.com/q/d/l/?s=^vkospi&i=d")[:300])
