"""Recreate database with proper schema from Alembic migration"""
import os
import shutil
from pathlib import Path

db_path = Path("data/expense_matcher.db")
backup_path = Path("data/expense_matcher.db.backup")

# Backup existing database
if db_path.exists():
    print(f"Backing up {db_path} to {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("Removing old database...")
    os.remove(db_path)
    print("Old database removed.")
else:
    print("No existing database found.")

print("\nNow run: alembic upgrade head")
print("This will create a fresh database with the correct schema.")
