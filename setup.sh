#!/bin/bash

echo "=========================================="
echo "Interview RAG System - Automated Setup"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if LM Studio is accessible
echo "🔍 Checking LM Studio connection..."
if curl -s http://127.0.0.1:1234/v1/models > /dev/null 2>&1; then
    echo "✅ LM Studio is accessible at http://127.0.0.1:1234"
else
    echo "⚠️  Warning: Cannot connect to LM Studio at http://127.0.0.1:1234"
    echo "   Please ensure LM Studio is running with qwen2.5-coder-14b-instruct:2"
    echo "   Continuing anyway..."
fi
echo ""

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p backend/data/uploads
mkdir -p backend/data/vector_stores
mkdir -p backend/data/documents
echo "✅ Directories created"
echo ""

# Build and start services
echo "🐳 Building and starting Docker containers..."
echo "   This may take a few minutes on first run..."
docker-compose up -d --build

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "❌ Error: Services failed to start"
    echo "   Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "🔧 Initializing database..."
sleep 5

# Create admin user
echo "👤 Creating admin user..."
docker-compose exec -T backend python -c "
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()

# Check if admin exists
existing_admin = db.query(User).filter(User.username == 'admin').first()
if existing_admin:
    print('Admin user already exists')
else:
    admin = User(
        email='admin@interview-rag.com',
        username='admin',
        hashed_password=get_password_hash('admin123'),
        full_name='System Administrator',
        is_admin=True,
        is_active=True
    )
    db.add(admin)
    db.commit()
    print('✅ Admin user created successfully')

db.close()
" 2>/dev/null || echo "⚠️  Database initialization pending..."

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "🌐 Access the application:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "👤 Admin Credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📝 Next Steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Login with admin credentials"
echo "   3. Go to Admin Panel and upload interview documents"
echo "   4. Create a regular user account"
echo "   5. Upload your resume (optional)"
echo "   6. Start an interview session!"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart:       docker-compose restart"
echo ""
echo "📚 Documentation:"
echo "   - QUICKSTART.md for quick guide"
echo "   - docs/INSTALLATION.md for detailed setup"
echo "   - docs/ARCHITECTURE.md for system design"
echo ""
echo "🎉 Happy interviewing!"
echo "=========================================="
