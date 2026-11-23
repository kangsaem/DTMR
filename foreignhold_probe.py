"""외국인 보유 비중(코스피 시가총액 중 외국인 보유 %) 자료 경로 찾기(2026-11-23 사용자)
후보: ① KRX 정보데이터시스템 전종목 외국인 보유량(MDCSTAT03701) → 시총 가중 합 ② pykrx ③ 네이버 지수 API 항목
과거 깊이 확인용으로 날짜 몇 개를 같이 봄"""
import json, subprocess, sys, requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
DATES = ["20261120", "20260730", "20200320", "20081024", "20000104"]


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return float("nan")


print("===== ① KRX 정보데이터시스템 MDCSTAT03701")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020301"})
try:
    r0 = S.get("https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020301", timeout=20)
    print("첫 페이지", r0.status_code, len(r0.text))
except Exception as e:
    print("첫 페이지 실패", e)
for host in ("https://data.krx.co.kr", "http://data.krx.co.kr"):
    for d in DATES:
        try:
            r = S.post(host + "/comm/bldAttendant/getJsonData.cmd", timeout=30, data={
                "bld": "dbms/MDC/STAT/standard/MDCSTAT03701", "locale": "ko_KR", "searchType": "1", "mktId": "STK",
                "trdDd": d, "share": "1", "csvxls_isNo": "false"})
            ct = r.headers.get("content-type", "")
            print(host, d, r.status_code, ct[:30], len(r.text))
            if "json" in ct or r.text.strip().startswith("{"):
                j = r.json(); rows = j.get("OutBlock_1") or j.get("output") or []
                print("  키", list(j.keys())[:6], "행", len(rows), "첫 행", json.dumps(rows[0], ensure_ascii=False)[:300] if rows else "")
                if rows:
                    tot = sum(num(x.get("TDD_CLSPRC")) * num(x.get("LIST_SHRS")) for x in rows)
                    frn = sum(num(x.get("TDD_CLSPRC")) * num(x.get("FORN_HD_QTY")) for x in rows)
                    print(f"  → 외국인 보유 비중(시총 가중) {frn / tot * 100:.2f}% · 종목 {len(rows)}")
            else:
                print("  본문", r.text[:200].replace("\n", " "))
        except Exception as e:
            print(host, d, "실패", type(e).__name__, str(e)[:150])
    print()

print("===== ② pykrx")
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pykrx"], check=True, timeout=180)
    from pykrx import stock
    for d in DATES[:3]:
        try:
            df = stock.get_exhaustion_rates_of_foreign_investment(d, "KOSPI")
            print(d, df.shape, list(df.columns)[:8]); print(df.head(3).to_string()[:400])
        except Exception as e:
            print(d, "실패", type(e).__name__, str(e)[:200])
except Exception as e:
    print("pykrx 설치/불러오기 실패", type(e).__name__, str(e)[:200])

print("===== ③ 네이버 지수 API")
H = {"User-Agent": UA, "Referer": "https://m.stock.naver.com/"}
for u in ["https://m.stock.naver.com/api/index/KOSPI/basic", "https://m.stock.naver.com/api/index/KOSPI/integration",
          "https://m.stock.naver.com/api/index/KOSPI/trend?bizdate=20261120"]:
    try:
        r = requests.get(u, headers=H, timeout=20)
        t = r.text
        hit = [k for k in ("foreign", "Foreign", "외국", "frgn") if k in t]
        print(u, r.status_code, len(t), "외국인 관련 글자", hit)
        if hit:
            i = min(t.find(k) for k in hit if t.find(k) >= 0); print("  ", t[max(0, i - 150):i + 250].replace("\n", " "))
    except Exception as e:
        print(u, "실패", e)
