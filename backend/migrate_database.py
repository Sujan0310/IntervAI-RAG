"""
Database Migration Script
Handles schema changes without losing data
"""
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings
from app.core.database import Base, engine
from app.models.user import User
from app.models.interview import Interview, InterviewQuestion, Resume

def get_table_columns(table_name):
    """Get current columns in a table"""
    inspector = inspect(engine)
    if table_name in inspector.get_table_names():
        return [col['name'] for col in inspector.get_columns(table_name)]
    return []

def column_exists(table_name, column_name):
    """Check if column exists in table"""
    columns = get_table_columns(table_name)
    return column_name in columns

def add_column_if_missing(table_name, column_name, column_def):
    """Add column to table if it doesn't exist"""
    if not column_exists(table_name, column_name):
        print(f"Adding column {column_name} to {table_name}...")
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
            conn.commit()
        print(f"✅ Column {column_name} added successfully")
        return True
    else:
        print(f"✓ Column {column_name} already exists in {table_name}")
        return False

def migrate_database():
    """Run all database migrations"""
    print("=" * 60)
    print("DATABASE MIGRATION")
    print("=" * 60)
    
    # Create all tables that don't exist
    print("\n1. Creating missing tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created/verified")
    
    # Check current schema
    print("\n2. Checking current schema...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Existing tables: {', '.join(tables)}")
    
    # Apply migrations
    print("\n3. Applying schema migrations...")
    migrations_applied = 0
    
    # Migration 1: Add resume_id to interviews table
    if add_column_if_missing('interviews', 'resume_id', 'INTEGER'):
        migrations_applied += 1
    
    # Future migrations can be added here
    # Example:
    # if add_column_if_missing('users', 'phone_number', 'VARCHAR'):
    #     migrations_applied += 1
    
    print(f"\n4. Migration summary:")
    print(f"   Tables: {len(tables)}")
    print(f"   Migrations applied: {migrations_applied}")
    
    # Verify final schema
    print("\n5. Verifying final schema...")
    for table in ['users', 'resumes', 'interviews', 'interview_questions']:
        columns = get_table_columns(table)
        print(f"   {table}: {len(columns)} columns")
        print(f"      {', '.join(columns)}")
    
    print("\n" + "=" * 60)
    print("✅ DATABASE MIGRATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    try:
        migrate_database()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
