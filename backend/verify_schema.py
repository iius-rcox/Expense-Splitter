"""Verify database schema for deduplication fields"""
from sqlalchemy import inspect
from models.base import engine

inspector = inspect(engine)

print('PDFs table columns:')
for col in inspector.get_columns('pdfs'):
    nullable = 'NULL' if col['nullable'] else 'NOT NULL'
    print(f'  - {col["name"]}: {col["type"]} ({nullable})')

print('\nPDFs table indexes:')
for idx in inspector.get_indexes('pdfs'):
    print(f'  - {idx["name"]}: {idx["column_names"]}')

print('\nPDFs table unique constraints:')
for uc in inspector.get_unique_constraints('pdfs'):
    print(f'  - {uc["name"]}: {uc["column_names"]}')

print('\n\nTransactions table columns:')
for col in inspector.get_columns('transactions'):
    nullable = 'NULL' if col['nullable'] else 'NOT NULL'
    print(f'  - {col["name"]}: {col["type"]} ({nullable})')

print('\nTransactions table indexes:')
for idx in inspector.get_indexes('transactions'):
    print(f'  - {idx["name"]}: {idx["column_names"]}')

print('\nTransactions table unique constraints:')
for uc in inspector.get_unique_constraints('transactions'):
    print(f'  - {uc["name"]}: {uc["column_names"]}')

print('\n✅ Schema verification complete!')
