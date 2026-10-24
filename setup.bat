@echo off
echo ==========================================
echo Interview RAG System - Automated Setup
echo ==========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker and try again.
    exit /b 1
)

echo Docker is running
echo.

REM Check if LM Studio is accessible
echo Checking LM Studio connection...
curl -s http://127.0.0.1:1234/v1/models >nul 2>&1
if errorlevel 1 (
    echo Warning: Cannot connect to LM Studio at http://127.0.0.1:1234
    echo Please ensure LM Studio is running with qwen2.5-coder-14b-instruct:2
    echo Continuing anyway...
) else (
    echo LM Studio is accessible at http://127.0.0.1:1234
)
echo.

REM Create necessary directories
echo Creating data directories...
if not exist "backend\data\uploads" mkdir backend\data\uploads
if not exist "backend\data\vector_stores" mkdir backend\data\vector_stores
if not exist "backend\data\documents" mkdir backend\data\documents
echo Directories created
echo.

REM Build and start services
echo Building and starting Docker containers...
echo This may take a few minutes on first run...
docker-compose up -d --build

REM Wait for services to be ready
echo.
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check if services are running
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo Error: Services failed to start
    echo Check logs with: docker-compose logs
    exit /b 1
)

echo Services are running
echo.

echo Initializing database...
timeout /t 5 /nobreak >nul

REM Create admin user
echo Creating admin user...
docker-compose exec -T backend python -c "from app.core.database import SessionLocal; from app.models.user import User; from app.core.security import get_password_hash; db = SessionLocal(); existing_admin = db.query(User).filter(User.username == 'admin').first(); admin = User(email='admin@interview-rag.com', username='admin', hashed_password=get_password_hash('admin123'), full_name='System Administrator', is_admin=True, is_active=True) if not existing_admin else None; db.add(admin) if admin else None; db.commit() if admin else None; print('Admin user created') if admin else print('Admin already exists'); db.close()" 2>nul

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Access the application:
echo    Frontend:  http://localhost:3000
echo    Backend:   http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo.
echo Admin Credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo Next Steps:
echo    1. Open http://localhost:3000 in your browser
echo    2. Login with admin credentials
echo    3. Go to Admin Panel and upload interview documents
echo    4. Create a regular user account
echo    5. Upload your resume (optional)
echo    6. Start an interview session!
echo.
echo Useful Commands:
echo    View logs:     docker-compose logs -f
echo    Stop services: docker-compose down
echo    Restart:       docker-compose restart
echo.
echo Happy interviewing!
echo ==========================================
pause
