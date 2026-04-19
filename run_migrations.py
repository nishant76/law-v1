#!/usr/bin/env python3
"""
Migration runner — execute Alembic migrations for Nikhar database
Usage: python run_migrations.py

Runs: alembic upgrade head
CWD:  backend/migrations/ (where alembic.ini lives)
"""
import subprocess
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "backend" / "migrations"


def main() -> int:
    print(f"Running migrations from: {MIGRATIONS_DIR}")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(MIGRATIONS_DIR),
    )
    if result.returncode == 0:
        print("Migrations completed successfully")
    else:
        print(f"Migration failed (exit code {result.returncode})")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
