# Berk's Book NBA Totals Lab v2 — free starter

A zero-paid-service, mobile-first NBA totals dashboard with a Python ingestion pipeline and scheduled GitHub Pages deployment. Predictions are **deliberately locked** until **10 qualifying games per team**. **No real wagers or automatic bets.**

## Get it online — start here

1. Create a free [GitHub account](https://github.com/signup) and a **new public repository** named `berks-book-nba`. Keep the repository public for free GitHub Pages.
2. Unzip this starter project. Upload **all project files and folders** into the root of your repository (include the hidden `.github/workflows/update-and-publish.yml` folder/file). One easy method is GitHub's **Add file → Upload files** and drag in files preserving the directory tree; GitHub Desktop or Git CLI is often easier for whole projects.
3. In your repository choose **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Open the **Actions** tab and run **Update NBA dashboard → Run workflow**. You may need to approve workflows. Wait until the workflow says it succeeded; then visit **Settings → Pages** for the dashboard URL: `https://YOURUSERNAME.github.io/berks-book-nba/`.
5. For automatic sportsbook lines, get the free 500-credit/month key at [The Odds API](https://the-odds-api.com/). Put it in **Settings → Secrets and variables → Actions → New repository secret** named **`ODDS_API_KEY`**. **Do not** paste the key into the website, repo code or chat. Rerun the workflow.
6. The dashboard will refresh at **8:17 AM and 5:47 PM America/New_York** daily, plus when triggered manually. GitHub's scheduled workflows can be delayed, and public-repository schedules may disable after 60 days of inactivity.

## What it does now

- Automatically tries to retrieve current 2026–27 NBA schedules, final scores and boxscores from ESPN's **unofficial** public endpoints. These are not guaranteed to be available, stable, or permitted indefinitely. Source failures leave the corresponding estimates blank instead of inventing numbers.
- Requests `basketball_nba`, `markets=totals`, `regions=us` from The Odds API. According to its current documented pricing, that costs **1 credit per successful request** (not per game). Two updates/day ≈ 60–62 credits/month, comfortably within 500. Keep the key secret. Some completed and missing games may not appear.
- Computes approximate pace and offensive/defensive efficiency from FGA, FTA, offensive rebounds and turnovers, using only regulation games **from Oct 20, 2026 onward**.
- Makes a shrinkage-adjusted projection *only after both teams have ≥10 valid current-season games*. It compares against bookmaker median available totals and labels ≥5.5-point differences as `WATCH OVER` or `WATCH UNDER`.
- Archives observed pregame sportsbook lines from day one. Once predictions unlock, saves a hypothetical pre-game selection before tipoff and grades it later. Odds are stored from the captured bookmaker; results are *paper* results only. It's not backtested or calibrated.

## Important limitations and next steps

- **This is a functional starter, not a validated betting model.** ESPN's third-party endpoints may change or refuse cloud runners. Initial deployment must verify that real games and team boxscores appear. Fix the ingestion or swap to a reliable permitted alternative before using the model.
- Injuries, starting lineups, minutes, rest and projected rotations **are not integrated**. The interface is transparent about this. No green 'bet' recommendation is shown.
- Historical pregame lines are not included on the free Odds API tier. The dashboard begins capturing its *own* twice-daily sampled market lines as soon as the free key is configured, even while predictions remain locked. Closing-line tracking requires an additional last-pretip refresh or a separate source.
- Other improvements: calibrated over/under probabilities, season backtesting and walk-forward evaluation, data-source health alerts, home/away and rest adjustments. None are included yet.
- The site is public on GitHub Pages. Do **not** put personal bankroll or account information into `data/` or `site/data/`.
- Public GitHub Pages + public GitHub Actions + standard-library Python + free Odds API means **no hosting/software/API fee** for this usage pattern, subject to providers' limits and policies.
- The local `data/archive.json`, `data/odds_snapshots.json`, and `data/paper_bets.json` are intended to be versioned into your repo to persist between scheduled jobs.

## Test or run locally

```bash
python -m unittest discover -s tests -v
# Live fetch (requires public internet; odds optional):
python scripts/update.py
cd site && python -m http.server 8000
# Open http://localhost:8000
```

## Formula (experimental)

Approx. team possessions: `FGA − offensive rebounds + turnovers + 0.44 × FTA`.

`off_rating = 100 × scored_pts / team_possessions`; `def_rating = 100 × allowed_pts / opponent_possessions`.

Pace estimate = mean of team possession counts per regulation game.

For each team's efficiency, shrink to the current league mean with weight `games / (games + 8)`. Project each team's efficiency as its shrunk offense + opponent shrunk defense − league mean. Then project total points as `expected pace × (matchup home efficiency + matchup away efficiency) / 100`.

This is a **baseline**, not a validated estimator of game total or win probability. Quantify MAE, bias, calibration and closing-line value on real pregame samples before acting on it.
