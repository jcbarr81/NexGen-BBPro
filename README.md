# UBL Simulation

UBL (Ultimate Baseball League) Simulation is a Python project that models a small baseball league with a graphical interface.

## Features
- **PyQt6 interface:** run `main.py` to launch the login window and access administrative tools.
- **League management:** classes for players, teams, trades and rosters in `models/` with supporting services and UI dialogs.
- **Game simulation:** `logic/simulation.py` provides a minimal engine for at-bats, pitching changes and base running.
- **Data files:** example data lives in the `data/` directory including rosters, lineups and configuration values.

### Play balance configuration

Strategy behaviour in the simulation is driven by values from the
`PlayBalance` section of the historical *PB.INI* file.  The configuration is
loaded into a dedicated :class:`PlayBalanceConfig` dataclass
(`logic/playbalance_config.py`) which exposes the entries as attributes with
safe defaults.  The managers and `GameSimulation` consume this object instead
of raw dictionaries.

For tests and experimentation a helper factory is provided in
`tests/util/pbini_factory.py` which can create minimal configurations:

```python
from tests.util.pbini_factory import make_cfg
cfg = make_cfg(offManStealChancePct=50)
```

## Lineup CSV Format
Lineup files live in `data/lineups/` and are named `<TEAM>_vs_lhp.csv` or `<TEAM>_vs_rhp.csv`.
Each file contains the columns:

```csv
order,player_id,position
```

`player_id` uses the internal IDs such as `P1000`.

## Development
Install the dependencies (see `requirements.txt`) then run:

```bash
python main.py
```


### Running tests
Tests are located in the `tests/` directory and can be executed with:

```bash
pytest
```

To run a single exhibition style scenario you can target an individual test,
for example:

```bash
pytest tests/test_simulation.py::test_run_tracking_and_boxscore -q
```

### Building an executable
Install PyInstaller and create a standalone binary with:

```bash
pip install -r requirements-dev.txt
python build_exe.py
```

The executable will be written to the `dist/` directory.

### Default Admin Credentials
When a new league is created or user accounts are cleared, the system rewrites
`data/users.txt` to contain a single administrator account. Use these fallback
credentials to log in after a reset:

```
username: admin
password: pass
```

