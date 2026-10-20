# AGENTS.md — rules for the daily news runs

This repo collects news for eight sectors and turns it into a short daily brief (Mon–Sat) and a full weekly roundup (Sunday). A GitHub Action pulls the feeds every 4 hours; a scheduled Claude run reads them each morning, checks for gaps, writes the report, commits it here and emails it. The scheduled task's prompt adds the private details (reader profile, email address, git author). Where this file and the prompt differ, the prompt wins.

## Sectors
Report order and short tag names:

| key | Sector | Tag |
|---|---|---|
| fusion | Fusion & plasma physics (ITER, tokamaks/stellarators, DIFFER, startups, funding, milestones) | Fusion |
| semis | Semiconductors & lithography (ASML, EUV, supply chain, export controls, Brainport) | Semis |
| ai | AI / ML research (notable models, papers, ML for science) | AI |
| simulation | Physics simulation (simulation software, GPU/HPC, digital twins, ML surrogates; Ansys, COMSOL, NVIDIA) | Simulation |
| hardware | Hardware manufacturing (lidar, sensors, actuators, humanoid parts, production scale-up) | Hardware |
| bigtech | Big tech (major moves, deals, earnings, policy) | Big tech |
| robotics | Robotics, incl. humanoids | Robotics |
| space | Aerospace & space | Space |

## Repo layout
- `sources.yaml` — the feeds (direct RSS/Atom and Google News searches), each tagged with a sector.
- `tools/fetch_feeds.py` — run by `.github/workflows/fetch.yml` every 4 hours. Writes `feed/YYYY/MM/YYYY-MM-DD.jsonl` (new items), `feed/status.json` (feed health), `feed/seen.tsv` (dedup).
- `tools/digest.py` — compact view of collected items for a time window (see below).
- `tools/deck.py` — builds the slide-deck PDF from a deck JSON.
- `stories/ongoing.md` — developing stories followed up every report.
- `state/last_run.json` — where the last report's window ended.
- `reports/YYYY/MM/` — archive: for each report the slide-deck `.pdf` (easiest to read), the `.md` text version and the `.deck.json`.

## Every run: window
Read `state/last_run.json`. The window runs from `cutoff_utc` to the moment this run starts (UTC, to the minute). If the file is missing or `cutoff_utc` is more than 3 days ago, use the last 24 hours (Sunday: 7 days) and say so in the report subtitle.

## Daily brief (Monday–Saturday)
1. **Feed items.** `python3 tools/digest.py --since <cutoff_utc>`. Read all of it. Lines are `id  time  outlet: headline  [+n: other outlets]`; similar headlines are merged and more-covered stories come first. If a sector hits the line cap, run `--sector <key> --max 200`. `--show <id> ...` prints the link and summary.
2. **Context.** Read `stories/ongoing.md` and the last 3 reports in `reports/`. Don't repeat an item already reported unless something new happened; then say what's new.
3. **Gap check.** Feeds miss things (paywalled outlets, wire stories). Run one WebSearch per sector for news in the window, plus one per ongoing story that has a decision, launch or deadline inside the window.
4. **Pick 5–8 items** for the whole brief, at most 3 per sector, ranked by importance to the reader. Prefer real change (a decision, result, launch, deal, money, policy) over commentary and previews. Wide coverage (`[+n]`) is a signal, not proof. A quiet day gets fewer items; never pad.
5. **Verify each pick.** Open the original article with WebFetch, or confirm with a second independent source. Google News links (`news.google.com/rss/articles/...`) don't open directly: WebSearch the headline, find the publisher's URL and cite that, never the Google News link. State numbers only as a source gives them. Paraphrase; no quotes longer than about 15 words.
6. **Ongoing stories** (rules below).
7. **Write** the archive file and the deck (formats below), build the PDF.
8. **State.** Write `state/last_run.json` with `kind: "daily"`, `date`, `cutoff_utc` = this window's end; keep `last_roundup_cutoff_utc` unchanged.
9. **Feed maintenance** (rules below).
10. **Commit and push**, then email (details in the prompt). Email even if the push fails, and say so in the email.

## Sunday roundup
Replaces Sunday's daily brief and also covers Sunday's own news.
- Window: `last_roundup_cutoff_utc` -> now (about 7 days).
- Inputs: this week's daily reports in `reports/`; `python3 tools/digest.py --since <last_roundup_cutoff_utc> --max 25`; the new items since `cutoff_utc` (treat those exactly like a daily brief's steps 1–5); `stories/ongoing.md`; one WebSearch per sector for anything big the dailies missed.
- Content: a 2–3 sentence topline on the week; per sector the 2–4 most significant developments of the week (repeating items from the dailies is expected here) and a one-word direction (accelerating, cooling, consolidating, steady, volatile, ...) backed by the evidence; every ongoing story with its status and whether it moved this week; resolved or dropped stories; what to watch next week with dates; feed health only if a feed has failed for 3+ days or `sources.yaml` changed this week.
- State: set both `cutoff_utc` and `last_roundup_cutoff_utc` to this window's end, `kind: "roundup"`.

## Ongoing stories
Format in `stories/ongoing.md`: `- <story> — <sector key> — since <date> — latest: <one-line status> (<date>)`.
- Every run: update `latest` and its date for each story that moved. Leave the others as they are.
- Add a story when something from this window will clearly continue: a pending decision or vote, an awaited launch or result, a deal not yet closed, an investigation, an earnings season.
- Remove a story when it is resolved, and state the outcome once in the report under "Resolved".
- Keep about 20. If over, drop the least relevant story with no news for 3+ weeks and nothing scheduled, and list it under "Resolved / dropped".

## Archive file
`reports/YYYY/MM/YYYY-MM-DD.md` (Sunday: `YYYY-MM-DD-roundup.md`), short:

```
---
kind: daily            # or roundup
period: 2026-10-21 Wed # or 2026-W43
window: 2026-10-20T05:50Z -> 2026-10-21T05:50Z
---
# Daily news — 2026-10-21 Wed
<topline, 2-3 sentences>

## Top news            (roundup: one section per sector with "Direction: <word>")
1. **<headline>** (<Tag>) — what happened. Why it matters. [Outlet](url)

## Stories that moved
- <story>: <latest>

## Resolved
## Worth watching
## Sources
```

Save the deck JSON next to it as `YYYY-MM-DD.deck.json` and the built PDF as `YYYY-MM-DD.pdf` (Sunday: `YYYY-MM-DD-roundup.deck.json`, `YYYY-MM-DD-roundup.pdf`). Always commit the PDF: it is the readable version of the report.

## Decks
Slide types and fields are in `tools/deck.py`: `statement`, `cards`, `table`, `bullets`, `sources` (the cover comes from `title`, `period`, `subtitle`, `topline`). Plain text only, "->" instead of arrow symbols, short text, one idea per slide. Build from the repo root:
`python3 tools/deck.py deck.json /tmp/report.pdf` (also writes `/tmp/report.pdf.b64`). If it errors, fix the JSON, not the design.

**Daily brief** — `{"theme": "news", "title": "Daily news", "period": "2026-10-21 Wed", "subtitle": "<window in Amsterdam time · N items>", "topline": "...", "slides": [...]}`. About 5–7 slides:
1. `statement` — the single most important item.
2. `cards` "Top news" — all picked items, 3 per slide (at most 3 slides). Card `tag` = sector tag; `tagkind` `"new"` if the item starts a new ongoing story, else `""`; `h` = headline; `p` = what happened; `m` = why it matters to the reader; `link` = source URL.
3. `table` "Stories that moved" — Story, Sector, Latest. Only stories that moved; if none, one row saying so. Add "Resolved: ..." rows if any.
4. `bullets` "Worth watching" — 2–4 things in the next 48 hours, with dates and Amsterdam times where known.
5. `sources`.

**Sunday roundup** — `{"theme": "market", "title": "Weekly roundup", "period": "2026-W43", ...}`. About 10–16 slides: `statement` (biggest move of the week) -> one `cards` slide per sector (kicker = sector name, `tag` = direction word, 2–4 cards; sectors with no meaningful news combined into one `bullets` slide) -> `table` "Ongoing stories" (Story, Sector, Since, Latest, Moved this week?; split over slides above ~10 rows) -> `bullets` "Resolved / dropped" if any -> `bullets` "Worth watching next week" -> `bullets` "Feed health" if needed -> `sources`.

## Feed maintenance
- `digest.py` prints feed health from `feed/status.json`. A feed with `fail_streak` of 18 or more (about 3 days) gets fixed: WebSearch for its current RSS URL and update `sources.yaml`; if there is none, remove the entry.
- If a strong outlet keeps turning up only through WebSearch across several runs, add its feed if it has one.
- At most 3 `sources.yaml` changes per run; name them in the commit message.
- If `status.json`'s `updated` is more than 12 hours old, the fetch Action has stopped: put that in the first line of the email.
- Don't edit `tools/` or the workflow unless something is broken.

## Writing
Brief and direct, no filler. "Why it matters" is about the reader's sectors and work, in one sentence. Times in Amsterdam time. Paraphrase sources.

## Commit
From the repo root: `git add -A reports stories state sources.yaml`, message `brief: YYYY-MM-DD` or `roundup: YYYY-Www` (plus any feed changes). The fetch Action commits every 4 hours, so run `git pull --rebase` before pushing; if the push fails, pull and push once more.
