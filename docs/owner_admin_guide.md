# Team Owner and Admin Guide

This guide explains how to operate the UBL Simulation application as a **team owner** or as an **administrator**. Launch the app with:

```bash
python main.py
```

After signing in, users are presented with dashboards tailored to their role.

## Team Owner Dashboard

Team owners manage their franchise through the Owner Dashboard.

### Roster Management
- View Active, AAA and Low rosters.
- Move players between levels using the dropdown and movement buttons.
- Cut players from a roster.
- Save the roster. Validation enforces:
  - Maximum 25 players and at least 11 position players on the Active roster.
  - Maximum 15 players on the AAA roster.
  - Maximum 10 players on the Low roster.

### Player and Lineup Tools
- **Position Players / Pitchers**: open detailed windows to inspect players by role.
- **Lineups**: launch the lineup editor to set batting orders.
- **Pitching Staff**: manage pitching roles and rotations.
- **Transactions**: view recent roster moves.
- **Settings**: adjust team colours, logos and other options.

### League Information
- **Standings** and **Schedule** windows give a league-wide overview.
- **Trades**: propose trades with other teams.
- **Free Agents**: automatically sign the first available free agent.
- **News Feed**: display the latest league news.

Unsaved roster changes are flagged with an asterisk in the window title.

## Admin Dashboard

Administrators control league configuration and high-level operations.

### League and User Management
- **Create League**: generate a new league structure (overwrites current data).
 - **Reset to Opening Day**: clear current season results and standings, reset progress to day one, and set the phase to Regular Season (non-destructive to teams/rosters). You will be prompted whether to also purge saved season boxscores (`data/boxscores/season`).
- **Add User**: create a new account with optional team assignment.
- **Edit User**: update passwords and team associations for existing accounts.
- **Open Team Dashboard**: launch any team's owner dashboard for direct management.

### Trade Oversight
- **Review Trades**: approve or reject pending trades submitted by teams.

### Utilities
- **Generate Team Logos**: create logo images for all teams.
- **Simulate Exhibition Game**: run a quick simulation between two teams.

### Amateur Draft
The Amateur Draft introduces new prospects mid-season and pauses the season to conduct the draft.

- Draft Timing: Draft Day is the third Tuesday in July (computed from the schedule).
  - The Draft page shows a status line with the current simulation date and Draft Day.
  - “View Draft Pool” and “Start/Resume Draft” enable only on/after Draft Day and only if the draft hasn’t been completed that year.
  - “Draft Settings” is always available.

- Draft Page Buttons:
  - **Draft Settings**: configure rounds, pool size, and RNG seed for reproducibility. Settings are saved to `data/draft_config.json`.
  - **View Draft Pool**: browse the prospect pool (enabled on/after Draft Day).
  - **Start/Resume Draft**: open the Draft Console to conduct the draft and resume mid-draft if needed (enabled on/after Draft Day).

- Draft Console Overview:
  - Pool table with search filter; pitchers display EN/CO/MV (endurance/control/movement).
  - On-the-clock banner indicating the current team and pick.
  - Recent picks board (last 10); state and results are persisted per pick.
  - Actions:
    - “Make Pick” to select the highlighted prospect.
    - “Auto Pick (This Team)” for an AI pick respecting organizational needs.
    - “Auto Draft All” to finish the remaining rounds automatically.
    - “Commit Draftees to Rosters” appends new players to `data/players.csv` and places them on each team’s `LOW` roster level.
  - Double-click a prospect to open their Player Profile for detailed ratings.

- Files and Persistence:
  - Draft Pool: `data/draft_pool_<year>.csv` and `data/draft_pool_<year>.json`.
  - Draft State: `data/draft_state_<year>.json` (order, current pick, selected ids, seed).
  - Draft Results (log): `data/draft_results_<year>.csv` (round, overall_pick, team_id, player_id).
  - Draft completion is tracked in `data/season_progress.json` under `draft_completed_years`.

Tip: Use a non-empty seed in Draft Settings for deterministic pool generation and draft order.

## Default Administrator Login
When user data is reset, a default administrator account is created. Although
most passwords are stored using `bcrypt` hashes, the fallback administrator
record is saved in plain text so the app remains accessible even if the
`bcrypt` dependency is missing. Use these credentials to access the Admin
Dashboard if no other accounts exist:

```
username: admin
password: pass
```

---
This document will evolve as new features are introduced.
