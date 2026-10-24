"""
Database initialization script
Creates tables and admin user
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.interview import Interview, InterviewQuestion, Resume
from app.core.security import get_password_hash

def init_database():
    """Initialize database with tables and admin user"""
    print("Creating database tables...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")
    
    # Create admin user
    db = SessionLocal()
    try:
        # Check if admin exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if existing_admin:
            print("ℹ️  Admin user already exists")
        else:
            admin = User(
                email="admin@interview-rag.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="System Administrator",
                is_admin=True,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("✅ Admin user created successfully")
            print("   Username: admin")
            print("   Password: admin123")
        
        # Create demo user
        existing_demo = db.query(User).filter(User.username == "demo").first()
        
        if not existing_demo:
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
            print("✅ Demo user created successfully")
            print("   Username: demo")
            print("   Password: demo123")
        
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n✅ Database initialization complete!")

if __name__ == "__main__":
    init_database()
