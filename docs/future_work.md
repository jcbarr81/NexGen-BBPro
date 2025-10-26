# Future Work Ideas

This note captures high-level enhancements identified during the latest review so
they are easy to revisit when planning new milestones.

## 1. Unified Data Service Layer
- **Goal:** Stop re-opening CSV/JSON files in every module by introducing a
  repository/service layer (see `docs/Architecture.md`). This would centralize
  persistence, reduce I/O contention, and unlock alternative backends (SQLite,
  cloud sync).
- **Scope:** Wrap common loaders (players, rosters, standings, transactions) in
  shared query/update APIs and expose an event bus so UI widgets can subscribe to
  changes instead of issuing file operations directly.

## 2. League History & Archive UI
- **Goal:** Surface the new season archives produced by
  `SeasonContext`/`LeagueRolloverService` inside the Admin dashboard.
- **Ideas:** Add a "League History" page showing champions, awards, standings,
  and playoff brackets per season; extend player/team profile dialogs with a
  season selector that reads from `data/careers/<season_id>/`.

## 3. Contracts & Financial Systems
- **Goal:** Expand the simple free-agency helpers into a richer contract model
  with budgets, multi-year deals, arbitration, and salary impact on trades.
- **Scope:** Extend `services/contract_negotiator`, add organization finances,
  and build UI (owner + admin) to review commitments, payroll, and cap space.

## 4. Deepened Player Development
- **Goal:** Turn the current "training camp marks everyone ready" flow into a
  meaningful development phase with focus tracks, morale, and aging effects.
- **Ideas:** Add training plans per player, hook into `playbalance/aging_model`,
  and reflect outcomes in ratings plus new tutorial/UX messaging.

## 5. Pitch Budget Telemetry & Tuning
- **Goal:** Finish the `docs/pitch_budget_model.md` roadmap by pushing budget
  metrics to the UI so commissioners can validate reliever workloads.
- **Scope:** Expose `available_pct`/rest info on dashboards, integrate
  `scripts/usage_calibration.py` summaries, and add tests to lock in MLB-like
  appearance/IP targets.

## 6. Outstanding Test Failures
- **Reminder:** `docs/failing_tests.md` still lists unchecked pytest targets
  (e.g., simulation averages, foul balls, stadium dimensions, stats windows).
  Clearing these before new features will keep regression risk low.

