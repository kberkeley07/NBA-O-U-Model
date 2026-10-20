BERK'S BOOK DUAL MODEL UPDATE — OCTOBER 2026

This patch adds your actual Excel v1 formula alongside the adjusted v2 algorithm.

Install from iPad Safari:
1. In Files, tap this ZIP to unzip it.
2. Open GitHub > kberkeley07/NBA-O-U-Model > Code > Add file > Upload files.
3. Upload these FIVE files to the REPOSITORY ROOT (not .github):
   update.py, app.js, index.html, styles.css, test_model.py
4. Commit changes, replacing the same-named files.
5. Go to Actions > Update NBA dashboard > Run workflow (branch main).
6. After a green deployment, reload the GitHub Pages dashboard.

IMPORTANT:
- Do not upload this ZIP itself, and do not upload README_INSTALL.txt.
- Keep the root file layout you used from your iPad; the existing GitHub Actions workflow arranges these files on deployment.
- Existing paper_bets.json and odds data are preserved.
- Preview forecasts before 10 qualifying games per team are NEVER counted as paper picks.
- At 10+ games, V1 and V2 signals are stored separately and graded separately.
- Both models use current-season estimated possessions/ratings, NOT old-season stats.
- Last year's spreadsheet reports 40-28 and +8.112810298 units, but a single editable Stats tab means the workbook does not verify timestamped pregame projections.
- This project relies on undocumented ESPN endpoints and can fail to receive data.
