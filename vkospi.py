"""VKOSPI(코스피 200 변동성지수) — KRX Open API로 받아 data/vkospi.csv에 쌓음 (2026-11-23)

출처: GET https://data-dbg.krx.co.kr/svc/apis/idx/drvprod_dd_trd?basDd=YYYYMMDD (헤더 AUTH_KEY = Secrets KRX_API_KEY)
  → OutBlock_1 중 IDX_NM '코스피 200 변동성지수'의 CLSPRC_IDX. 한 번에 하루치만 옴 → 날짜마다 호출(키당 하루 10,000건).
  휴장일은 빈 목록. 그날 자료는 보통 다음 날 아침에 올라옴(장 마감 직후 실행이면 전 거래일까지).
사용: python vkospi.py backfill [시간제한분]   # 비어 있으면 2009-04-13부터, 있으면 마지막 날 다음부터
      python vkospi.py check                   # 파일 요약
"""
import csv, json, os, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone

FILE = "data/vkospi.csv"
START = date(2009, 4, 13)          # VKOSPI 공식 산출 시작일
URL = "https://data-dbg.krx.co.kr/svc/apis/idx/drvprod_dd_trd?basDd={}"
NAME = "코스피 200 변동성지수"
KST = timezone(timedelta(hours=9))


def load():
    """[(date, close)] 날짜 순"""
    if not os.path.exists(FILE):
        return []
    with open(FILE, encoding="utf-8") as f:
        return [(date.fromisoformat(r["date"]), float(r["close"])) for r in csv.DictReader(f)]


def save(rows):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    rows = sorted(dict(rows).items())
    with open(FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        for d, c in rows:
            w.writerow([d.isoformat(), f"{c:.2f}"])


def fetch_day(d, key):
    """그날 VKOSPI 종가, 휴장·미게시면 None. 인증·통신 오류는 예외"""
    req = urllib.request.Request(URL.format(d.strftime("%Y%m%d")), headers={"AUTH_KEY": key, "User-Agent": "Mozilla/5.0"})
    for i in range(3):
        try:
            j = json.loads(urllib.request.urlopen(req, timeout=20).read())
            break
        except Exception:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    for x in j.get("OutBlock_1") or []:
        if x.get("IDX_NM") == NAME:
            v = str(x.get("CLSPRC_IDX", "")).replace(",", "")
            return float(v) if v not in ("", "-") else None
    return None


def update(limit_min=None, log=print):
    """마지막 저장일 다음 날 ~ 오늘(KST)까지 평일을 받아 저장. limit_min 분이 지나면 중간 저장 후 멈춤(다시 실행하면 이어감)"""
    key = os.environ.get("KRX_API_KEY", "")
    if not key:
        raise RuntimeError("KRX_API_KEY 없음")
    rows = load()
    have = {d for d, _ in rows}
    d = (rows[-1][0] + timedelta(days=1)) if rows else START
    today = datetime.now(KST).date()
    t0, n_call, n_new = time.time(), 0, 0
    while d <= today:
        if d.weekday() < 5 and d not in have:
            v = fetch_day(d, key)
            n_call += 1
            if v is not None:
                rows.append((d, v)); n_new += 1
            if n_call % 200 == 0:
                save(rows); log(f"  {d} 까지 {n_call}회 호출 · 새 {n_new}일")
            if limit_min and time.time() - t0 > limit_min * 60:
                break
        d += timedelta(days=1)
    save(rows)
    return {"calls": n_call, "new": n_new, "last": rows[-1][0].isoformat() if rows else None, "n": len(rows)}


def series():
    """pandas Series(날짜 → 종가). 파일이 없으면 빈 Series"""
    import pandas as pd
    rows = load()
    return pd.Series([c for _, c in rows], index=pd.to_datetime([d for d, _ in rows]), dtype=float)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "backfill":
        lim = float(sys.argv[2]) if len(sys.argv) > 2 else None
        print(update(lim))
    rows = load()
    if rows:
        cs = [c for _, c in rows]
        print(f"{len(rows)}일 {rows[0][0]} ~ {rows[-1][0]} · 최저 {min(cs):.2f} 최고 {max(cs):.2f} · 마지막 {rows[-1][1]:.2f}")
    else:
        print("자료 없음")
