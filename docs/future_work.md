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

## 7. Multi-League Ownership & Collaboration Roadmap
These initiatives enable a single owner to juggle multiple leagues, move saves
between offline/online modes, and collaborate with other owners through
messaging, chat, and forums. Tackle them in the order below so shared services
land before channel-specific features.

### 7.1 Multiple Offline Leagues per Owner
1. **Domain model:** Introduce `Owner` → `LeagueProfile` → `Season` entities plus
   ownership/role tables so one owner can switch contexts safely.
2. **Storage:** Centralize persistence in a franchise service layer (SQLite or
   repo abstraction) that keeps per-league saves isolated yet linked to an owner.
3. **Config templates:** Allow each league to define rule sets, schedules, AI
   levels, and presentation settings; expose template cloning for quick setups.
4. **Owner dashboard:** Build a cross-league hub showing active leagues, alerts,
   save health, and shortcuts (resume sim, manage roster, pending trades).
5. **Portability:** Ship export/import for leagues (JSON or SQLite bundle) so a
   user can share leagues across machines while staying offline.

### 7.2 Online League Path
1. **File-sync phase:** Define canonical export format (manifest + hashes) so
   commissioners can exchange updates via shared storage and detect conflicts.
2. **Deterministic sims:** Ensure simulation steps remain reproducible by
   locking PRNG seeds and logging state transitions.
3. **Client/server prototype:** Spin up a FastAPI (or similar) service exposing
   REST for admin actions plus WebSocket for live events; add token auth.
4. **Hosted persistence:** Move authoritative league state to the server and run
   sims in background jobs/queues; clients issue signed commands only.
5. **Migration tooling:** Provide upgrade scripts that ingest existing offline
   saves and register owners/teams on the server without data loss.

### 7.3 Direct Owner Messaging
1. **Message model:** Create conversation threads tied to a league, team, or
   generic DM; include participant roles and read receipts.
2. **API layer:** Expose CRUD endpoints and subscription events (WebSocket)
   through the franchise services layer so UI clients stay in sync.
3. **Inbox UI:** Add an in-app mailbox with filters (league, unread, mentions)
   plus quick-reply composer referencing players, trades, or fixtures.
4. **Notifications:** Integrate with the existing notification center (toast,
   email hooks) and allow owners to tune per-thread alerts.
5. **Moderation:** Support blocking/muting, audit logs, and retention policies
   so commissioners can enforce community guidelines.

### 7.4 Built-in Chat Rooms
1. **Transport:** Reuse the WebSocket broker for real-time chat; fallback to
   long-polling in offline/file-sync mode.
2. **Rooms:** Define chat scopes (league lobby, draft room, ad-hoc topic) and
   persist membership + history for late joiners.
3. **Draft integration:** Embed chat alongside draft board/pick clock so owners
   can coordinate, share scouting cards, and auto-post picks.
4. **UX polish:** Add mentions, emoji, attachments (player cards, lineup files),
   and moderation controls (mute, kick, slow mode).
5. **Observability:** Log chat events for diagnostics and expose metrics (active
   users, message volume) to ensure scalability.

### 7.5 Forums, Trade Block & News
1. **Forum taxonomy:** Create categories for Trade Block, League News, Strategy,
   Support; allow commissioners to manage visibility.
2. **Content model:** Support Markdown/Rich Text, tagging of players/teams, and
   linking to sims or stats so posts stay contextual.
3. **Trade block workflows:** Enable owners to flag players, auto-generate post
   templates, and notify other GMs/subscribers.
4. **Automation hooks:** Let the sim engine publish recaps, award announcements,
   or injury reports directly into forum channels.
5. **Moderation & discovery:** Add pinning, reactions, search, and archival
   policies, plus integrate forum notifications with the inbox/chat system.
