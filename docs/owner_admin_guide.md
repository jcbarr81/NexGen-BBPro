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
- **Add User**: create a new account with optional team assignment.
- **Edit User**: update passwords and team associations for existing accounts.

### Trade Oversight
- **Review Trades**: approve or reject pending trades submitted by teams.

### Utilities
- **Generate Team Logos**: create logo images for all teams.
- **Simulate Exhibition Game**: run a quick simulation between two teams.

## Default Administrator Login
When user data is reset, a default administrator account is created:

```
username: admin
password: pass
```

Use these credentials to access the Admin Dashboard if no other accounts exist.

---
This document will evolve as new features are introduced.
