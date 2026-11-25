"""코스피 외국인 순매수(억원, 하루) — 네이버 m.stock api/index/KOSPI/trend?bizdate 로 받아 data/foreign_kospi.csv에 쌓음 (2026-11-25)
위험 지표 '코스피 52주 고점 -3% 이내인데 외국인 20일 순매도'용. 처음 자료 = results/foreign_kospi.json(2026-10-15 bottom_cmp가 모은 것)의 2024년부터.
휴장일·아직 없는 날은 bizdate가 달라 건너뜀(다음 실행에서 다시 시도)."""
import csv, json, os, time
from datetime import date, datetime, timedelta, timezone
import requests

FILE = "data/foreign_kospi.csv"
KST = timezone(timedelta(hours=9))
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}


def load():
    rows = []
    if os.path.exists(FILE):
        with open(FILE, encoding="utf-8") as f:
            for r in csv.reader(f):
                if r and r[0] != "date":
                    rows.append((date.fromisoformat(r[0]), float(r[1])))
    return rows


def save(rows):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    rows = sorted(dict(rows).items())
    with open(FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "foreign"])
        for d, v in rows:
            w.writerow([d.isoformat(), f"{v:.0f}"])


def fetch_day(d):
    s = d.strftime("%Y%m%d")
    for i in range(3):
        try:
            j = requests.get(f"https://m.stock.naver.com/api/index/KOSPI/trend?bizdate={s}", headers=H, timeout=15).json()
            if j.get("bizdate") != s:
                return None
            return float(str(j["foreignValue"]).replace(",", "").replace("+", ""))
        except Exception:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))


def update(limit_min=3, log=print):
    rows = load()
    if not rows and os.path.exists("results/foreign_kospi.json"):          # 처음: 모아 둔 자료에서 2024년부터
        j = json.load(open("results/foreign_kospi.json"))
        rows = [(date(int(k[:4]), int(k[4:6]), int(k[6:])), float(v)) for k, v in j.items() if k >= "20240101"]
    have = {d for d, _ in rows}
    d = (max(have) + timedelta(days=1)) if have else date(2024, 1, 2)
    today, t0, new = datetime.now(KST).date(), time.time(), 0
    while d <= today and time.time() - t0 < limit_min * 60:
        if d.weekday() < 5 and d not in have:
            v = fetch_day(d)
            if v is not None:
                rows.append((d, v)); new += 1
        d += timedelta(days=1)
    save(rows)
    return {"new": new, "last": max(r[0] for r in rows).isoformat() if rows else None, "n": len(rows)}


def series():
    import pandas as pd
    rows = load()
    return pd.Series({pd.Timestamp(d): v for d, v in rows}).sort_index() if rows else pd.Series(dtype=float)


if __name__ == "__main__":
    print(update())
