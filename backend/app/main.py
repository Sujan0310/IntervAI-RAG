"""
Main FastAPI application entry point
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.api import auth, interview, admin, analytics, rag

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Interview RAG System...")
    
    # Run database migrations
    logger.info("Running database migrations...")
    try:
        import sys
        sys.path.append('.')
        from migrate_database import migrate_database
        migrate_database()
        logger.info("Database migrations complete")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        # Don't fail startup, but log the error
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Initialize RAG components
    from app.rag.embedding.embedder import EmbeddingService
    from app.rag.retrieval.hybrid_retriever import HybridRetriever
    
    try:
        embedding_service = EmbeddingService()
        logger.info("Embedding service initialized")
        
        retriever = HybridRetriever()
        logger.info("Hybrid retriever initialized")
        
        # Auto-index documents from knowledge base
        logger.info("Auto-indexing knowledge base documents...")
        import sys
        sys.path.append('.')
        from auto_index_documents import index_documents_from_folder
        result = index_documents_from_folder()
        logger.info(f"Auto-indexing complete: {result['total_files']} files, {result['total_chunks']} chunks")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG components: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Interview RAG System...")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Next-Generation Intelligent Interview Preparation System using Advanced RAG",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Interview RAG System",
        "version": "1.0.0",
        "strict_rag_mode": settings.STRICT_RAG_MODE
    }


# Database health check endpoint
@app.get("/health/database")
async def database_health_check(db: Session = Depends(get_db)):
    """Database health check endpoint"""
    try:
        from sqlalchemy import inspect, text
        
        # Test connection
        db.execute(text("SELECT 1"))
        
        # Check schema
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Check required tables
        required_tables = ['users', 'resumes', 'interviews', 'interview_questions']
        missing_tables = [t for t in required_tables if t not in tables]
        
        # Check required columns in interviews table
        if 'interviews' in tables:
            columns = [col['name'] for col in inspector.get_columns('interviews')]
            required_columns = ['id', 'user_id', 'resume_id', 'title', 'domain']
            missing_columns = [c for c in required_columns if c not in columns]
        else:
            missing_columns = required_columns
        
        # Check foreign keys (SQLite)
        fk_enabled = False
        if settings.DATABASE_URL.startswith("sqlite"):
            result = db.execute(text("PRAGMA foreign_keys")).fetchone()
            fk_enabled = result[0] == 1 if result else False
        
        return {
            "status": "healthy" if not missing_tables and not missing_columns else "degraded",
            "database": {
                "connected": True,
                "tables": len(tables),
                "missing_tables": missing_tables,
                "missing_columns": missing_columns,
                "foreign_keys_enabled": fk_enabled
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Interview RAG System API",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
