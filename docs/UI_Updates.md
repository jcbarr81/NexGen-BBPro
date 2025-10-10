UI & User Experience

Break the 1,700-line admin dashboard monolith into feature modules and introduce shared navigation/state primitives, which will speed up rendering and make future pages (e.g., analytics) easier to plug in (ui/admin_dashboard.py:314).
Offload long-running actions like logo/portrait generation and league auto-setup onto background QThreads or QtConcurrent futures instead of running them on the UI thread with manual processEvents loops (ui/admin_dashboard.py:728, ui/season_progress_window.py:732); pair them with toast notifications and retry controls.
Augment the owner scoreboard panel with trend charts, bullpen readiness, and matchup scouting sourced from the quick-metrics helper (ui/owner_dashboard.py:94) to shorten the path from overview to actionable decisions.
Expand the player profile dialog with mini spray charts and rolling stat graphs by integrating lightweight plotting (ui/player_profile_dialog.py:1); combine with comparison mode so owners can stack prospects side-by-side.
Turn the season progress window into an interactive timeline that highlights auto-sim milestones, draft checkpoints, and playoff clinch scenarios, giving admins a visual roadmap (ui/season_progress_window.py:1).

## Implementation Task List

### Priority P1 - Admin Dashboard Foundation
- [x] Audit `ui/admin_dashboard.py` to map current feature groupings, navigation flows, and shared state needs. -- Pages: dashboard/home, league, teams, users, utilities, draft; each funnels button events to `MainWindow` helpers for trades, league resets, team automation, draft consoles, and asset generation. Shared state pivots on `self.pages`, `self.nav_buttons`, and `self.team_dashboards`, with long-running routines tied to league resets, logo/avatar generation, roster automation, and file-heavy season management.
- [x] Design a modular structure for the admin dashboard (feature packages plus shared navigation/state primitives). -- See "Admin Dashboard Modularization Plan (Groundwork)" outlining package layout, shared primitives (`DashboardContext`, `NavigationController`), page modules, action modules, and phased migration.
- [x] Scaffold the new modules so future migrations can move logic in stages. -- Introduced `ui/admin_dashboard/` package with compatibility shim, `main_window.py`, shared `context.py`/`navigation.py`, placeholder `pages/` + `actions/` modules, and parked the monolith in `ui/_admin_dashboard_legacy.py`.
- [x] Incrementally migrate each dashboard feature into its module and wire the shared navigation/state layer back into `ui/admin_dashboard.py`. -- Home/overview now lives under `ui/admin_dashboard/pages/home.py`, the package exports the modular `MainWindow` (with the legacy class available as `LegacyMainWindow`), and navigation wiring covers the modular pages while retaining legacy actions.

### Priority P2 - Async Actions & Feedback
- [x] Catalogue long-running actions in `ui/admin_dashboard.py` and `ui/season_progress_window.py`, noting inputs/outputs and current UI feedback. -- See "Long-running Action Catalogue (P2)" below.
- [x] Implement background execution wrappers (QThread or QtConcurrent) for the identified long-running actions and remove UI-thread `processEvents` loops. -- Season progress now falls back to an internal `ThreadPoolExecutor`, the legacy `_simulate_span_sync` path (and its manual `processEvents` loop) has been retired in favor of async execution with a cancel control, and all long-running admin/season flows are off the UI thread.
- [x] Add toast notifications and retry controls for background actions, ensuring consistent messaging across admin and season progress windows. -- Toasts now surface start/finish for logos, avatars, league resets, season progress simulations, playoff runs, summary exports, and the playoff viewer summary open flow; export/open errors raise Retry-capable dialogs for quick reattempts.

#### Long-running Action Catalogue (P2)

##### Admin Dashboard (`ui/_admin_dashboard_legacy.py` and `ui/admin_dashboard/actions/*`)
| Action | Trigger | Inputs | Output / Side Effects | Current UI Feedback | Threading |
| --- | --- | --- | --- | --- | --- |
| `create_league_action` (`actions/league.py`) | League page -> "Create League" | User-provided league name, divisions, teams-per-division, team structure from `TeamEntryDialog` | Rewrites `data` directory via `playbalance.league_creator.create_league`; overwrites teams, schedules, rosters | Confirmation dialogs for overwrite and errors; final info message; no toast plumbing | Runs on UI thread (synchronous) |
| `reset_season_to_opening_day` (`actions/league.py`) | League page -> "Reset to Opening Day" | Confirmation prompt; optional boxscore purge flag | Rewrites `schedule.csv`, resets `season_progress.json`, clears standings/stats/history, optionally deletes `data/boxscores/season` | Info toast on start; success/error toast on completion; modal message boxes mirror outcome | Uses `DashboardContext.run_async` (background future) |
| `generate_team_logos_action` (`actions/assets.py`) | Utilities page -> "Generate Team Logos" | None | Invokes `utils.logo_generator.generate_team_logos` to emit logo files under data assets | Info toast while running; success/error toasts and message boxes with output path | Uses `DashboardContext.run_async` |
| `generate_player_avatars_action` (`actions/assets.py`) | Utilities page -> "Generate Player Avatars" | Optional "initial creation" flag gathered from dialog | Calls `utils.avatar_generator.generate_player_avatars`; rewrites avatar assets | Info toast during run; success/error toasts and modal message boxes | Uses `DashboardContext.run_async` |
| `set_all_lineups` (`actions/teams.py`) | Teams page -> "Set All Team Lineups" | Iterates `data/teams.csv`, `players.csv`, roster/lineup directories | Runs `auto_fill_lineup_for_team` per club; rewrites lineup files; collects failures | Final message box (info or warning listing teams); no toasts | Runs on UI thread; can block during large leagues |
| `set_all_pitching_roles` (`actions/teams.py`) | Teams page -> "Set All Pitching Staff Roles" | `players.csv`, team rosters; writes `*_pitching.csv` | Computes staff assignments via `autofill_pitching_staff`; rewrites pitching CSVs | Message boxes for success or permission errors; no toast coverage | Runs on UI thread; loops across all teams |
| `auto_reassign_rosters` (`actions/teams.py`) | Teams page -> "Auto Reassign All Rosters" | Uses `services.roster_auto_assign.auto_assign_all_teams`; reads roster/player files | Writes updated roster CSVs; audits defensive coverage and reports issues | Message boxes for success/warnings; no toasts | Runs on UI thread; cross-league operation |

##### Season Progress Window (`ui/season_progress_window.py`)
| Action | Trigger | Inputs | Output / Side Effects | Current UI Feedback | Threading |
| --- | --- | --- | --- | --- | --- |
| `_simulate_day` | "Simulate Day" button | Current `SeasonSimulator`, schedule validity, lineup/roster state | Simulates single date via `self.simulator.simulate_next_day`; updates progress, merges stats, logs recaps | Modal warnings on lineup/draft issues; updates `notes_label`/`remaining_label`; no toasts | Runs on UI thread |
| `_simulate_span_async` | "Simulate Week/Month/To Phase" buttons when `run_async` available | Days count, season simulator, lineup validation | Background loop simulating up to requested span; merges stats, writes progress, handles cancellations | Disables sim controls; info toast on start; success/warning/error toasts on completion; modal warnings when applicable | Uses injected `run_async`; safe cancel cleanup |
| `_simulate_span_sync` | Same buttons when no `run_async` provided | Same as above | UI-thread loop with `QProgressDialog`; manual `QApplication.processEvents`; same disk writes as async path | Progress dialog with cancel button; warning dialogs on errors; no toast support | Runs on UI thread with busy-wait pattern |
| `_simulate_playoffs_async` | "Simulate Playoffs"/phase advance when async available | Current standings, playoffs config, bracket files | Executes `_playoffs_workflow` in background; writes bracket/champions records; updates season phase | Info toast on start; success/error toasts on completion; message boxes mirror status | Uses `run_async`; registers cancel cleanup |
| `_simulate_playoffs_sync` | Same trigger when `run_async` absent | Same as above | Runs `_playoffs_workflow` on UI thread; blocks until complete | Message boxes for result; no toast coverage | Runs on UI thread |

### Priority P3 - Owner & Player Insights
- [x] Extend the quick-metrics helper to expose bullpen readiness, matchup scouting, and trend data needed by `ui/owner_dashboard.py`.
- [x] Build trend charts, bullpen readiness indicators, and matchup scouting widgets into the owner scoreboard panel.
- [x] Integrate lightweight plotting for player spray charts and rolling stat graphs inside `ui/player_profile_dialog.py`.
- [x] Implement comparison mode within the player profile dialog to allow side-by-side prospect evaluation.

### Priority P4 - Season Progress Timeline & QA
- [x] Define the data model for the season progress timeline, covering auto-sim milestones, draft checkpoints, and playoff clinch scenarios.
- [x] Create the interactive timeline UI in `ui/season_progress_window.py`, including event highlighting and tooltip details.
- [x] Update automated tests/docs to reflect the new UI architecture, asynchronous workflows, and analytics surfaces.

#### Admin Dashboard Modularization Plan (Groundwork)
- Module layout: convert `ui/admin_dashboard.py` into a `ui/admin_dashboard/` package with `__init__.py`, a slim `main_window.py`, and a `legacy_entry.py` shim to keep current imports working during migration.
- Shared primitives: add `context.py` defining a `DashboardContext` (base paths, service helpers, background executor) and `navigation.py` hosting a `NavigationController` plus reusable `PageRegistry`.
- Page modules: under `ui/admin_dashboard/pages/`, create `base.py` (`DashboardPage` with `attach(context)`/`refresh()` hooks) and dedicated modules for `home`, `league`, `teams`, `users`, `utilities`, and `draft`.
- Action modules: collect the operational routines into `ui/admin_dashboard/actions/` (`trades.py`, `league.py`, `teams.py`, `users.py`, `assets.py`, `draft.py`) so UI widgets trigger small coordinator methods calling these commands.
- Migration phases: (1) move widget/page classes into `pages` while keeping callbacks in place; (2) shift long functions into `actions` leveraging the shared context; (3) replace direct references in `MainWindow` with registry-driven wiring; (4) retire the shim and delete the old monolith once parity is confirmed.

## Owner Dashboard Enhancement Backlog

Ideas captured from the current redesign pass; keep in the backlog until we allocate implementation time.

- **Scenario Snapshot Card**: Replace or augment the Trendlines space with a hybrid card that shows the next opponent (probable starters, weather, pitching matchup) and the latest game recap so the default view is meaningful even when long-term trend data is empty.
- **Actionable Alerts Strip**: Add a slim column or banner for actionable items (injured players cleared, expiring contracts, pending trades) with deep links into the relevant workflow dialogs.
- **Micro Performance Widgets**: Introduce compact cards for offense/pitching (e.g., runs per game, bullpen leverage usage) alongside Team Snapshot to provide at-a-glance context without scrolling.
- **Responsive Sidebar Tweaks**: On tablet-width breakpoints collapse the sidebar into icons or a hamburger so the main dashboard retains breathing room without requiring full-screen.
- **Quick Action Segmentation**: Group quick-action buttons into logical tabs or segmented controls (Lineup Tools vs. League Views) and consider keyboard shortcuts for the top actions to reduce the visual list length.
- **Richer News Feed**: Add type icons and filters (team-only, league-wide) plus inline “open in dialog” affordances so owners can triage updates quickly.
- **Customizable Layout**: Allow owners to pin/reorder widgets or toggle optional cards (financials, attendance, farm system snapshots) to tailor the dashboard to their workflow.

