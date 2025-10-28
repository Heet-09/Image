#!/bin/bash

# Deployment script for Image CBIR Application
# Usage: ./deploy.sh

echo "========================================="
echo "  Image CBIR Application Deployment"
echo "========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo ""
echo "✅ Docker and Docker Compose are installed"
echo ""

# Prompt for configuration
echo "📝 Configuration (Press Enter for defaults)"
read -p "MySQL Database Name [cbir_db]: " MYSQL_DATABASE
MYSQL_DATABASE=${MYSQL_DATABASE:-cbir_db}

read -p "MySQL User [user]: " MYSQL_USER
MYSQL_USER=${MYSQL_USER:-user}

read -sp "MySQL Password: " MYSQL_PASSWORD
echo ""

read -sp "MySQL Root Password: " MYSQL_ROOT_PASSWORD
echo ""
echo ""

# Update docker-compose.prod.yml with new values
echo "📝 Updating docker-compose.prod.yml..."
sed -i "s/MYSQL_DATABASE: cbir_db/MYSQL_DATABASE: $MYSQL_DATABASE/g" docker-compose.prod.yml
sed -i "s/MYSQL_USER: user/MYSQL_USER: $MYSQL_USER/g" docker-compose.prod.yml
sed -i "s/MYSQL_PASSWORD: password/MYSQL_PASSWORD: $MYSQL_PASSWORD/g" docker-compose.prod.yml
sed -i "s/MYSQL_ROOT_PASSWORD: rootpassword/MYSQL_ROOT_PASSWORD: $MYSQL_ROOT_PASSWORD/g" docker-compose.prod.yml

echo "✅ Configuration updated"
echo ""

# Build and start containers
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.prod.yml build

echo ""
echo "🚀 Starting containers..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run migrations
echo ""
echo "📊 Running database migrations..."
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
echo ""
echo "📁 Collecting static files..."
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Show status
echo ""
echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
echo ""
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "🌐 Application is available at:"
echo "   - http://localhost/"
echo "   - http://localhost:8000/"
echo ""
echo "📝 Useful commands:"
echo "   View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "   Stop app: docker-compose -f docker-compose.prod.yml down"
echo "   Restart: docker-compose -f docker-compose.prod.yml restart"
echo ""

