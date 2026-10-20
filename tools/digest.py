#!/usr/bin/env python3
"""Compact view of the collected feed items, for the daily brief and the Sunday roundup.

  python3 tools/digest.py --since 2026-10-20T05:50:00Z      items fetched after this time
  python3 tools/digest.py --hours 24                         items fetched in the last 24 h
  python3 tools/digest.py --since ... --sector fusion        one sector only
  python3 tools/digest.py --show a1b2c3d4e5 f6a7b8c9d0       full record (link, summary) for ids

Items are grouped by sector. Similar headlines from different outlets are merged into one
line ("+3: Reuters, CNBC, ...") and lines with more outlets come first: more coverage
usually means a bigger story. Times are Amsterdam time.
"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
FEED = ROOT / "feed"
AMS = ZoneInfo("Europe/Amsterdam")
SECTORS = ["fusion", "semis", "ai", "simulation", "hardware", "bigtech", "robotics", "space"]
NAMES = {"fusion": "Fusion & plasma", "semis": "Semiconductors & lithography", "ai": "AI / ML research",
         "simulation": "Physics simulation", "hardware": "Hardware manufacturing", "bigtech": "Big tech",
         "robotics": "Robotics", "space": "Aerospace & space"}
STOP = set("a an the of to in on for and or with by at from as is are be its it this that new after over "
           "into amid says said will has have how why what".split())


def parse_time(s):
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def load(since, until):
    items = []
    day = since.astimezone(AMS).date() - timedelta(days=1)
    last = until.astimezone(AMS).date()
    while day <= last:
        p = FEED / f"{day:%Y/%m/%Y-%m-%d}.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    items.append(json.loads(line))
        day += timedelta(days=1)
    out = []
    for it in items:
        f = parse_time(it["fetched"])
        if not (since < f <= until):
            continue
        if it.get("published") and parse_time(it["published"]) < since - timedelta(hours=36):
            continue  # old article that a feed surfaced late
        out.append(it)
    return out


def words(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in STOP and len(w) > 2}


def cluster(items, thr=0.5):
    groups = []
    for it in sorted(items, key=lambda x: x.get("published") or x["fetched"]):
        w = words(it["title"])
        for g in groups:
            gw = g["words"]
            if w and gw and len(w & gw) / len(w | gw) >= thr:
                g["items"].append(it)
                break
        else:
            groups.append({"words": w, "items": [it]})
    return groups


def stamp(it):
    t = parse_time(it.get("published") or it["fetched"]).astimezone(AMS)
    return f"{t:%m-%d %H:%M}"


def feed_health():
    p = FEED / "status.json"
    if not p.exists():
        return "feed health: no status.json yet"
    st = json.loads(p.read_text())
    feeds = st["feeds"]
    bad = [f"{n} ({s['fail_streak']}x)" for n, s in feeds.items() if not s["ok"]]
    line = f"feed health ({st['updated']}): {len(feeds) - len(bad)}/{len(feeds)} ok"
    return line + (f"; failing: {', '.join(bad)}" if bad else "")


def show(ids):
    want = set(ids)
    for p in sorted(FEED.glob("*/*/*.jsonl"), reverse=True):
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            if it["id"] in want:
                want.discard(it["id"])
                print(json.dumps(it, ensure_ascii=False, indent=1))
        if not want:
            break
    for i in want:
        print(f"{i}: not found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--hours", type=float)
    ap.add_argument("--until")
    ap.add_argument("--sector", choices=SECTORS)
    ap.add_argument("--max", type=int, default=40, help="max lines per sector")
    ap.add_argument("--show", nargs="+")
    a = ap.parse_args()
    if a.show:
        return show(a.show)
    until = parse_time(a.until) if a.until else datetime.now(timezone.utc)
    if a.since:
        since = parse_time(a.since)
    else:
        since = until - timedelta(hours=a.hours or 24)
    items = load(since, until)
    print(f"window {since.astimezone(AMS):%Y-%m-%d %H:%M} -> {until.astimezone(AMS):%Y-%m-%d %H:%M} "
          f"Amsterdam; {len(items)} items")
    print(feed_health())
    for sec in ([a.sector] if a.sector else SECTORS):
        sitems = [i for i in items if i["sector"] == sec]
        groups = cluster(sitems)
        groups.sort(key=lambda g: (-len({i["source"] for i in g["items"]}),
                                   -max(parse_time(i.get("published") or i["fetched"]).timestamp()
                                        for i in g["items"])))
        print(f"\n## {NAMES[sec]} ({len(sitems)} items, {len(groups)} stories)")
        for g in groups[: a.max]:
            first = g["items"][0]
            others = sorted({i["source"] for i in g["items"][1:]} - {first["source"]})
            extra = f"  [+{len(others)}: {', '.join(others[:4])}{', ...' if len(others) > 4 else ''}]" if others else ""
            print(f"{first['id']}  {stamp(first)}  {first['source']}: {first['title']}{extra}")
        if len(groups) > a.max:
            print(f"... {len(groups) - a.max} more (use --sector {sec} --max 200)")


if __name__ == "__main__":
    main()
