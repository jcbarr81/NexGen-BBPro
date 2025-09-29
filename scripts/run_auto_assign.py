from pathlib import Path
import sys

# Ensure repository root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.roster_auto_assign import auto_assign_all_teams


def main() -> None:
    auto_assign_all_teams()
    print("Auto assignment complete")


if __name__ == "__main__":
    main()
