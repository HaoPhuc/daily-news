# daily-news

News collection and daily briefs for eight sectors: fusion & plasma, semiconductors & lithography, AI/ML, physics simulation, hardware manufacturing, big tech, robotics, and aerospace & space.

- **Collect** — a GitHub Action pulls about 40 RSS feeds and Google News searches every 4 hours ([`sources.yaml`](sources.yaml)), deduplicates, and stores new items in [`feed/`](feed). Feed health: [`feed/status.json`](feed/status.json).
- **Brief** — every morning a scheduled Claude run reads the collected items, fills gaps with web search, verifies what it picks, and writes a short brief (Mon–Sat) or a full weekly roundup (Sunday). Each report is emailed as a slide-deck PDF and archived in [`reports/`](reports) as PDF (open it on GitHub to read) plus a text version.
- **Follow up** — developing stories are tracked in [`stories/ongoing.md`](stories/ongoing.md) until they resolve.

Rules for the runs: [`AGENTS.md`](AGENTS.md).

Look at recent items yourself (standard library only):

```
python3 tools/digest.py --hours 24
python3 tools/digest.py --hours 24 --sector fusion
```
