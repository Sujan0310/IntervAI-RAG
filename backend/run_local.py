"""
Local development server without Docker
Uses SQLite instead of PostgreSQL
"""
import os
import sys
from pathlib import Path

# Set environment variables for local development
os.environ['DATABASE_URL'] = 'sqlite:///./interview_rag.db'
os.environ['LLM_TYPE'] = 'lmstudio'
os.environ['LMSTUDIO_BASE_URL'] = 'http://127.0.0.1:1234'
os.environ['LMSTUDIO_MODEL'] = 'qwen2.5-coder-14b-instruct:2'
os.environ['LMSTUDIO_API_KEY'] = 'not-needed'
os.environ['EMBEDDING_TYPE'] = 'local'
os.environ['EMBEDDING_MODEL'] = 'sentence-transformers/all-MiniLM-L6-v2'
os.environ['SECRET_KEY'] = 'local-dev-secret-key-change-in-production'
os.environ['ENVIRONMENT'] = 'development'

print("=" * 60)
print("Starting Interview RAG System (Local Mode)")
print("=" * 60)
print()
print("Configuration:")
print(f"  Database: SQLite (interview_rag.db)")
print(f"  LLM: {os.environ['LMSTUDIO_MODEL']}")
print(f"  LLM URL: {os.environ['LMSTUDIO_BASE_URL']}")
print(f"  Embeddings: Local (SentenceTransformers)")
print()

# Create data directories
Path("data/uploads").mkdir(parents=True, exist_ok=True)
Path("data/vector_stores").mkdir(parents=True, exist_ok=True)
Path("data/documents").mkdir(parents=True, exist_ok=True)

# Initialize database
print("Initializing database...")
try:
    from app.core.database import engine, Base
    from app.models.user import User
    from app.models.interview import Interview, InterviewQuestion, Resume
    
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Create admin and demo users
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash
    
    db = SessionLocal()
    
    # Check if admin exists
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            email="admin@interview-rag.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            is_admin=True,
            is_active=True
        )
        db.add(admin)
        print("✅ Admin user created (admin/admin123)")
    else:
        print("ℹ️  Admin user already exists")
    
    # Check if demo exists
    demo = db.query(User).filter(User.username == "demo").first()
    if not demo:
        demo = User(
            email="demo@interview-rag.com",
            username="demo",
            hashed_password=get_password_hash("demo123"),
            full_name="Demo User",
            is_admin=False,
            is_active=True
        )
        db.add(demo)
        print("✅ Demo user created (demo/demo123)")
    else:
        print("ℹ️  Demo user already exists")
    
    db.commit()
    db.close()
    
except Exception as e:
    print(f"⚠️  Database initialization: {e}")

print()
print("=" * 60)
print("Starting FastAPI server...")
print("=" * 60)
print()
print("Backend will be available at: http://localhost:8000")
print("API Documentation: http://localhost:8000/docs")
print()
print("Press Ctrl+C to stop the server")
print()

# Start uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
