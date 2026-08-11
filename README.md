# newswire-watch

Polls free newswire RSS/Atom feeds, matches releases against a watchlist of company
names, and emails matches from `stewartbriggs655@gmail.com` to
`mmautom_258@outlook.com`. Runs on GitHub Actions' free tier - no server, no paid APIs.

Repo: https://github.com/DATAMANCA/PR_Release

## Sources (all free, no API key)

- PRNewswire: All News, Financial Services, Health, Biotechnology, Computer & Electronics, Consumer Technology
- GlobeNewswire: Public Companies
- SEC EDGAR: real-time 8-K filings (material corporate events)

**Known limitation:** PRNewswire and GlobeNewswire feeds only expose their most
recent ~20 items each. On a busy news day that window can turn over in well under
10 minutes, so infrequent polling risks missing releases. SEC EDGAR's feed returns
up to 100 items and isn't affected by this. The workflow polls every 5 minutes,
which reduces but doesn't eliminate the risk.

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

## How it runs

`.github/workflows/poll.yml` runs `src/main.py` every 5 minutes via GitHub Actions
cron. Each run:
1. Fetches all source feeds
2. Skips anything already recorded in `state/seen.json`
3. Emails everything new that matches the watchlist (one email per run, batching all matches found that run)
4. Commits the updated `state/seen.json` back to the repo so state persists between runs

The very first run just records every currently-live item as "seen" without
emailing - otherwise you'd get a flood of a few hundred backlog items on day one.

If the email fails to send (bad credentials, network blip, Gmail hiccup), the run
fails and that match is deliberately **not** marked as seen - it gets picked up and
retried on the next run instead of being silently lost. Everything else
(non-matches) is still recorded as seen immediately either way.

A `concurrency` guard prevents a manual "Run workflow" dispatch from overlapping
with a scheduled run - without it, both could start from the same state and
double-email the same match.

## Setup

### 1. Create a Gmail App Password for stewartbriggs655@gmail.com

SMTP login needs an App Password, not the regular account password.

1. Sign in to that Gmail account.
2. Go to https://myaccount.google.com/security
3. Turn on **2-Step Verification** if it isn't already on.
4. Once on, go to https://myaccount.google.com/apppasswords
5. Create an app password - name it something like `newswire-watch`.
6. Copy the 16-character password shown.

### 2. Push this code to https://github.com/DATAMANCA/PR_Release

```bash
cd newswire-watch
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/DATAMANCA/PR_Release.git
git branch -M main
git push -u origin main
```

### 3. Add repo secrets

Already added under **Settings → Secrets and variables → Actions**:

- `APP_PASSWORD` - the Gmail App Password from step 1
- `SENT` - `stewartbriggs655@gmail.com` (the sender/SMTP login)
- `TO` - `mmautom_258@outlook.com` (the recipient)

### 4. Allow the workflow to push commits

**Settings → Actions → General → Workflow permissions** → select
**"Read and write permissions"** → Save.

(This lets the workflow commit `state/seen.json` back to the repo after each run.)

### 5. Test it manually

**Actions tab → Newswire Poll → Run workflow**. Check the run logs - first run should
say "Bootstrap run: seeded N known items, no email sent." Run it again a bit later;
if any new release matches your watchlist you'll get an email.

## Running locally instead

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
copy .env.example .env       # then fill in SENT / TO / APP_PASSWORD
python src/main.py
```

`.env` is gitignored - never commit it. Locally, credentials are read from `.env`;
on GitHub Actions, they come from the repo secrets above via the workflow's `env:` block.

## Limitations

- **Not truly real-time.** GitHub Actions scheduled workflows aren't guaranteed to
  run exactly on schedule - GitHub documents that scheduled runs can be delayed,
  especially during high load. Treat this as "checks every 5-15 minutes," not
  instant push alerts.
- **GitHub auto-disables scheduled workflows after 60 days of repo inactivity.**
  The bot's own state commits should keep resetting that clock as long as it keeps
  finding new items - but if it goes quiet for 60+ days, re-enable manually from
  the Actions tab.
- **No true real-time wire (PRNewswire/BusinessWire full firehose, Dow Jones,
  Bloomberg, etc.) is free.** This uses the free public RSS categories those
  services expose, plus SEC EDGAR.
