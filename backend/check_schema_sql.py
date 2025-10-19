"""Check database schema using raw SQL"""
import sqlite3
from pathlib import Path

db_path = Path("data/expense_matcher.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== PDFs table schema ===")
cursor.execute("PRAGMA table_info(pdfs)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]} (NULL={row[3]==0})")

print("\n=== Transactions table schema ===")
cursor.execute("PRAGMA table_info(transactions)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]} (NULL={row[3]==0})")

print("\n=== Alembic version ===")
cursor.execute("SELECT version_num FROM alembic_version")
print(f"  Current: {cursor.fetchone()[0]}")

conn.close()
print("\nSchema check complete")
