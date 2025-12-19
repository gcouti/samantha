#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add the CLI service directory to sys.path to allow importing app.py
BASE_DIR = Path(__file__).resolve().parent
CLI_DIR = BASE_DIR / "services" / "ms-cli-interface"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import app  # noqa: E402


def main() -> None:
    asyncio.run(app.main())


if __name__ == "__main__":
    main()
