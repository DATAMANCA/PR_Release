# newswire-watch

Polls free newswire RSS/Atom feeds, matches releases against a watchlist of company
names, and emails matches from `stewartbriggs655@gmail.com` to
`mmautom_258@outlook.com`. Runs locally via Windows Task Scheduler every 5 minutes -
no server, no paid APIs.

Repo: https://github.com/DATAMANCA/PR_Release (code storage only - nothing runs on
GitHub Actions anymore, see "Why not GitHub Actions" below)

## Sources (all free, no API key)

- PRNewswire: All News, Financial Services, Health, Biotechnology, Computer & Electronics, Consumer Technology
- GlobeNewswire: Public Companies
- SEC EDGAR: real-time 8-K filings (material corporate events)

## Watchlist

Edit [config/watchlist.yaml](config/watchlist.yaml). Terms are specific company
names/tickers grouped by the ETF/theme they came from (`QQQ`, `SPY`, `DRAM`, `IGV`,
`XLV`) purely for your own organization - all terms are pooled into one flat list
for matching. Matching is case-insensitive and whole-word/phrase (regex `\b...\b`),
against each release's title + summary.

Deliberately avoids generic category words (e.g. "software", "biotech") - testing
showed those match too much unrelated noise (a press release about an insurance app
matched "software" despite having nothing to do with the sector). Stick to specific
company names/tickers when adding more.

Common single-word company names (Apple, Visa, Tesla, Oracle, Adobe, Workday) are
qualified with "Inc"/"Corporation" to avoid colliding with the same word used
generically ("business visa increase", "consulted an oracle", "flexible workday
policy" - all confirmed false-positive matches in testing before this was added).
Matching is whole-word, so "Visa Inc" won't accidentally match inside "visa
increase" the way plain substring matching did. If you add more single-word company
names, apply the same pattern - qualify them unless the name is genuinely unique
(e.g. "Micron", "Nvidia" don't need it).

## Why not GitHub Actions

This originally ran on GitHub Actions' free scheduled-workflow tier. In practice,
on a brand-new account/repo, GitHub's `schedule` trigger fired at 2-7 hour
intervals instead of the configured 5 minutes - anti-abuse throttling, not a config
error (everything checkable was correctly set: workflow active, permissions,
cron syntax, offset off round marks). Combined with PRNewswire/GlobeNewswire only
exposing their ~20 most recent items, multi-hour gaps meant releases were rolling
out of those feeds before ever being polled - so real matches were being missed
almost entirely. Moved to a local Windows Task Scheduler job instead, which runs
on real 5-minute ticks since it isn't subject to that throttling.

The GitHub repo is now code storage / version history only - nothing executes
there.

## How it runs

`scripts/run_poller.ps1` runs `src/main.py` every 5 minutes via a Windows Task
Scheduler job (`NewswireWatch`). Each run:
1. Fetches all source feeds
2. Skips anything already recorded in `state/seen.json`
3. Emails everything new that matches the watchlist (one email per run, batching all matches found that run)
4. Updates `state/seen.json` locally so state persists between runs

The very first run just records every currently-live item as "seen" without
emailing - otherwise you'd get a flood of a few hundred backlog items on day one.

If the email fails to send (bad credentials, network blip, Gmail hiccup), the run
fails and that match is deliberately **not** marked as seen - it gets picked up and
retried on the next run instead of being silently lost. Everything else
(non-matches) is still recorded as seen immediately either way.

`state/seen.json` is gitignored - it's local runtime state now, not committed back
to the repo.

## Setup

### 1. Create a Gmail App Password for stewartbriggs655@gmail.com

SMTP login needs an App Password, not the regular account password.

1. Sign in to that Gmail account.
2. Go to https://myaccount.google.com/security
3. Turn on **2-Step Verification** if it isn't already on.
4. Once on, go to https://myaccount.google.com/apppasswords
5. Create an app password - name it something like `newswire-watch`.
6. Copy the 16-character password shown.

### 2. Set up locally

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
copy .env.example .env       # then fill in SENT / TO / APP_PASSWORD
python src\main.py           # test run
```

`.env` is gitignored - never commit it.

### 3. Register the Task Scheduler job

```powershell
schtasks /create /tn "NewswireWatch" /tr "powershell.exe -ExecutionPolicy Bypass -File \"<repo path>\scripts\run_poller.ps1\"" /sc minute /mo 5 /f
```

Check `state\run.log` after a few cycles to confirm it's firing and see each run's
output (bootstrap/matches/errors).

## Limitations

- **Only runs while this machine is on.** Unlike a cloud scheduler, Task Scheduler
  can't fire while the PC is off/asleep - missed windows are just skipped (no
  backlog replay beyond what's still in each feed's current window when it next runs).
- **No true real-time wire (PRNewswire/BusinessWire full firehose, Dow Jones,
  Bloomberg, etc.) is free.** This uses the free public RSS categories those
  services expose, plus SEC EDGAR.
- **Known limitation:** PRNewswire and GlobeNewswire feeds only expose their most
  recent ~20 items each. On a busy news day that window can turn over in well under
  10 minutes, so infrequent polling risks missing releases. SEC EDGAR's feed returns
  up to 100 items and isn't affected by this. Polling every 5 minutes on real ticks
  (see above) reduces but doesn't eliminate the risk.
