"""
Create demo users in the database
"""
import os
import sys

# Set environment for SQLite
os.environ['DATABASE_URL'] = 'sqlite:///./interview_rag.db'

from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.interview import Interview, InterviewQuestion, Resume
from app.core.security import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    # Delete existing users
    db.query(User).delete()
    db.commit()
    
    # Create admin user
    admin = User(
        email="admin@interview-rag.com",
        username="admin",
        hashed_password=get_password_hash("admin123"),
        full_name="System Administrator",
        is_admin=True,
        is_active=True
    )
    db.add(admin)
    
    # Create demo user
    demo = User(
        email="demo@interview-rag.com",
        username="demo",
        hashed_password=get_password_hash("demo123"),
        full_name="Demo User",
        is_admin=False,
        is_active=True
    )
    db.add(demo)
    
    db.commit()
    
    print("✅ Users created successfully!")
    print("   Admin: admin / admin123")
    print("   Demo:  demo / demo123")
    
    # Verify
    users = db.query(User).all()
    print(f"\n📊 Total users in database: {len(users)}")
    for user in users:
        print(f"   - {user.username} ({user.email}) - Admin: {user.is_admin}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
