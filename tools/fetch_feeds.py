#!/usr/bin/env python3
"""Pull every feed in sources.yaml and store the new items.

Run by .github/workflows/fetch.yml every 4 hours.
Writes:
  feed/YYYY/MM/YYYY-MM-DD.jsonl  new items, one JSON object per line (day = Amsterdam date of the fetch)
  feed/seen.tsv                  ids already stored (link id and title id), pruned after SEEN_DAYS
  feed/status.json               per-feed health: ok, entries, new, error, last_ok, fail_streak
Day files older than KEEP_DAYS are deleted.
"""
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import yaml

ROOT = Path(__file__).resolve().parent.parent
FEED = ROOT / "feed"
AMS = ZoneInfo("Europe/Amsterdam")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 daily-news-fetcher (+https://github.com/HaoPhuc/daily-news)")
MAX_AGE = timedelta(hours=72)   # skip items published longer ago than this
KEEP_DAYS = 45                  # delete day files older than this
SEEN_DAYS = 30                  # forget stored ids after this
SECTORS = ["fusion", "semis", "ai", "simulation", "hardware", "bigtech", "robotics", "space"]
TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|cmpid|ncid|oc$)")


def gnews_url(query, lang="en"):
    hl, gl, ceid = {"en": ("en-US", "US", "US:en"), "nl": ("nl", "NL", "NL:nl")}[lang]
    qs = urllib.parse.urlencode({"q": f"{query} when:2d", "hl": hl, "gl": gl, "ceid": ceid})
    return "https://news.google.com/rss/search?" + qs


def norm_link(link):
    p = urllib.parse.urlsplit(link.strip())
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not TRACKING.match(k.lower())]
    path = p.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower().removeprefix("www."), path,
                                    urllib.parse.urlencode(q), ""))


def title_key(title):
    words = re.findall(r"[a-z0-9]+", title.lower())
    return " ".join(words)


def hid(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def clean(s, n):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def when(entry):
    for k in ("published_parsed", "updated_parsed"):
        t = entry.get(k)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    return None


def fetch(src):
    url = src.get("url") or gnews_url(src["query"], src.get("lang", "en"))
    err = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8"})
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read()
            d = feedparser.parse(body)
            if not d.entries and (d.bozo or b"<rss" not in body[:2000] and b"<feed" not in body[:2000]):
                err = f"no entries ({d.get('bozo_exception', 'not a feed')!r})"[:200]
            else:
                return src, url, d.entries, None
        except Exception as e:  # network errors, HTTP errors, timeouts
            err = f"{type(e).__name__}: {e}"[:200]
        time.sleep(3)
    return src, url, None, err


def main():
    cfg = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    feeds = cfg["feeds"]
    names = [f["name"] for f in feeds]
    if len(names) != len(set(names)):
        sys.exit("duplicate feed names in sources.yaml")
    for f in feeds:
        if f.get("sector") not in SECTORS:
            sys.exit(f"unknown sector for {f['name']}: {f.get('sector')}")

    junk = [re.compile(x, re.I) for x in cfg.get("exclude_titles") or []]
    now = datetime.now(timezone.utc)
    today = now.astimezone(AMS).date()
    FEED.mkdir(exist_ok=True)

    seen_path = FEED / "seen.tsv"
    seen = {}
    if seen_path.exists():
        for line in seen_path.read_text().splitlines():
            k, _, d = line.partition("\t")
            if k:
                seen[k] = d
    status_path = FEED / "status.json"
    old_status = json.loads(status_path.read_text())["feeds"] if status_path.exists() else {}

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch, feeds))

    new_items, status = [], {}
    for src, url, entries, err in results:
        prev = old_status.get(src["name"], {})
        st = {"sector": src["sector"], "url": url, "ok": err is None, "entries": 0, "new": 0,
              "last_ok": prev.get("last_ok"), "fail_streak": 0}
        if err:
            st["error"] = err
            st["fail_streak"] = prev.get("fail_streak", 0) + 1
            status[src["name"]] = st
            continue
        st["entries"] = len(entries)
        st["last_ok"] = now.isoformat(timespec="seconds")
        is_gn = "query" in src
        for e in entries:
            title, link = clean(e.get("title"), 300), (e.get("link") or "").strip()
            if not title or not link:
                continue
            source = src["name"]
            if is_gn:
                pub = (e.get("source") or {}).get("title") or ""
                if pub:
                    source = pub
                    if title.endswith(" - " + pub):
                        title = title[: -len(pub) - 3].rstrip()
            if any(j.search(title) for j in junk):
                continue
            published = when(e)
            if published and now - published > MAX_AGE:
                continue
            lid, tid = hid(norm_link(link)), hid(title_key(title))
            if lid in seen or tid in seen:
                continue
            seen[lid] = seen[tid] = today.isoformat()
            new_items.append({
                "id": lid,
                "sector": src["sector"],
                "title": title,
                "source": source,
                "published": published.isoformat(timespec="seconds") if published else None,
                "fetched": now.isoformat(timespec="seconds"),
                "link": link,
                "summary": "" if is_gn else clean(e.get("summary") or e.get("description"), 400),
                "via": src["name"],
            })
            st["new"] += 1
        status[src["name"]] = st

    day_file = FEED / f"{today:%Y/%m/%Y-%m-%d}.jsonl"
    day_file.parent.mkdir(parents=True, exist_ok=True)
    with day_file.open("a", encoding="utf-8") as fh:
        for it in new_items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")

    cutoff = (today - timedelta(days=SEEN_DAYS)).isoformat()
    seen_path.write_text("".join(f"{k}\t{d}\n" for k, d in sorted(seen.items()) if d >= cutoff))
    status_path.write_text(json.dumps({"updated": now.isoformat(timespec="seconds"),
                                       "feeds": status}, indent=1, ensure_ascii=False) + "\n")

    keep = today - timedelta(days=KEEP_DAYS)
    for p in FEED.glob("*/*/*.jsonl"):
        try:
            if datetime.strptime(p.stem, "%Y-%m-%d").date() < keep:
                p.unlink()
        except ValueError:
            pass
    for d in sorted(FEED.glob("*/*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    ok = sum(s["ok"] for s in status.values())
    print(f"{len(new_items)} new items; feeds ok {ok}/{len(status)}")
    for n, s in status.items():
        if not s["ok"]:
            print(f"  FAIL {n}: {s['error']}")


if __name__ == "__main__":
    main()
