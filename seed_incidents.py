from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    agent_dir = Path(__file__).resolve().parent / "agent-incident-history"
    sys.path.insert(0, str(agent_dir))
    runpy.run_path(str(agent_dir / "seed_incidents.py"), run_name="__main__")


if __name__ == "__main__":
    main()
