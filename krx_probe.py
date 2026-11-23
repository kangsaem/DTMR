"""KRX Open API 확인(2026-11-23): 파생상품지수(drvprod_dd_trd)·KOSPI 시리즈(kospi_dd_trd)에 VKOSPI가 있는지, 응답 형식
키 = Secrets KRX_API_KEY (probe.yml이 환경변수로 넘김). 키 값은 출력하지 않음."""
import json, os, urllib.request
from datetime import datetime, timedelta, timezone
KEY = os.environ.get("KRX_API_KEY", "")
print("키", "있음" if KEY else "없음(Secrets KRX_API_KEY 확인)")
K = timezone(timedelta(hours=9)); d = datetime.now(K)
days = []
while len(days) < 3:                        # 최근 평일 3일
    d -= timedelta(days=1)
    if d.weekday() < 5: days.append(d.strftime("%Y%m%d"))
for api in ("idx/drvprod_dd_trd", "idx/kospi_dd_trd"):
    for host in ("https://data-dbg.krx.co.kr/svc/apis/", "https://openapi.krx.co.kr/svc/apis/"):
        for bd in days[:1] if "kospi" in api else days:
            u = f"{host}{api}?basDd={bd}"
            try:
                r = urllib.request.urlopen(urllib.request.Request(u, headers={"AUTH_KEY": KEY, "User-Agent": "Mozilla/5.0"}), timeout=20)
                j = json.loads(r.read()); rows = j.get("OutBlock_1") or []
                print("OK", u, "| 행", len(rows), "| 키", list(rows[0].keys()) if rows else j)
                for x in rows:
                    nm = str(x.get("IDX_NM", ""))
                    if "변동성" in nm or "VKOSPI" in nm.upper() or "200" in nm and "kospi" not in api:
                        print("   ", json.dumps(x, ensure_ascii=False))
            except Exception as e:
                print("실패", u, repr(e)[:200])
        if any(True for _ in []): break
