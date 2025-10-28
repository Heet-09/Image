# Deployment Guide - Image CBIR Application

## Overview
This guide explains how to deploy the Docker-based image search (CBIR) application to a new server.

## Prerequisites

### On the new server:
- Docker installed (version 20.10+)
- Docker Compose installed (version 2.0+)
- Git (optional, for cloning)
- At least 2GB RAM (4GB recommended)
- At least 10GB disk space

### Verify installations:
```bash
docker --version
docker-compose --version
```

## Step 1: Copy Files to Server

### Option A: Using Git (Recommended)
```bash
# On the new server
git clone <your-repo-url>
cd Image
```

### Option B: Copy files manually
Copy these files/directories to the server:
```
Image/
├── cbir_app/          # Django app
├── cbir_project/       # Django settings
├── data/              # (optional)
├── media/             # (optional - user uploads)
├── static/            # (will be auto-generated)
├── nginx/             # Nginx config
├── requirements.txt
├── Dockerfile
├── docker-compose.prod.yml
├── manage.py
└── README.md
```

## Step 2: Configure Environment

### Update docker-compose.prod.yml
Edit these settings in `docker-compose.prod.yml`:

```yaml
environment:
  MYSQL_DATABASE: your_db_name
  MYSQL_USER: your_db_user
  MYSQL_PASSWORD: your_secure_password  # Change this!
  MYSQL_ROOT_PASSWORD: your_root_password  # Change this!
```

**Important**: Change the passwords!

## Step 3: Build and Start Application

### Initial setup:
```bash
# Navigate to project directory
cd Image

# Build and start all containers
docker-compose -f docker-compose.prod.yml up -d --build
```

This will:
- Download/build required images
- Start MySQL database
- Start Django web application
- Start Nginx reverse proxy

### Check status:
```bash
docker-compose -f docker-compose.prod.yml ps
```

Expected output should show 3 containers running:
- image-db-1 (MySQL)
- image-web-1 (Django)
- image-nginx-1 (Nginx)

## Step 4: Database Setup

### Run migrations:
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### Create superuser (optional, for admin access):
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## Step 5: Collect Static Files

### Generate static files:
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## Step 6: Verify Deployment

### Check logs:
```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs

# View only web logs
docker-compose -f docker-compose.prod.yml logs -f web
```

### Test endpoints:
- Homepage: http://your-server-ip:80/
- Search: http://your-server-ip:80/cbir/search/
- Upload: http://your-server-ip:80/cbir/upload/

## Step 7: Firewall Configuration

### If using a firewall, open required ports:
```bash
# For Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp  # Optional - for direct Django access

# For CentOS/RHEL
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

## Production Considerations

### 1. Security Updates
Update passwords in docker-compose.prod.yml
```yaml
MYSQL_PASSWORD: CHANGE_THIS_PASSWORD
MYSQL_ROOT_PASSWORD: CHANGE_THIS_TOO
```

### 2. SSL/HTTPS (Important for Production)
Set up SSL certificate with Let's Encrypt or similar.

Update nginx configuration to use HTTPS.

### 3. Environment Variables
Consider using `.env` file for sensitive data:
```bash
# Create .env file
MYSQL_PASSWORD=your_password
MYSQL_ROOT_PASSWORD=your_root_password
DJANGO_SECRET_KEY=your_secret_key
```

### 4. Backup Strategy
Set up regular database backups:
```bash
# Manual backup
docker-compose exec db mysqldump -u root -p cbir_db > backup.sql

# Automated backups (cron job)
0 2 * * * docker-compose exec db mysqldump -u root -pPASSWORD cbir_db > /backups/backup_$(date +\%Y\%m\%d).sql
```

### 5. Monitoring
Monitor container health:
```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check resource usage
docker stats

# View container logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Common Operations

### Restart application:
```bash
docker-compose -f docker-compose.prod.yml restart web
```

### Restart all services:
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Stop application:
```bash
docker-compose -f docker-compose.prod.yml down
```

### Update application:
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### View logs:
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f web

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Access Django shell:
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py shell
```

### Access database directly:
```bash
docker-compose -f docker-compose.prod.yml exec db mysql -u root -p cbir_db
```

## Troubleshooting

### Container won't start:
```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs

# Check docker status
docker ps -a
```

### Database connection errors:
```bash
# Ensure database is running
docker-compose -f docker-compose.prod.yml ps db

# Check database logs
docker-compose -f docker-compose.prod.yml logs db
```

### Permission errors:
```bash
# Fix media directory permissions
sudo chown -R 1000:1000 media/
sudo chmod -R 755 media/
```

### Out of memory:
```bash
# Check resource usage
docker stats

# Increase memory limits in docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 2G
```

## Quick Reference

### Useful commands:
```bash
# View all containers
docker ps -a

# View docker-compose containers
docker-compose -f docker-compose.prod.yml ps

# Stop everything
docker-compose -f docker-compose.prod.yml down

# Start everything
docker-compose -f docker-compose.prod.yml up -d

# Rebuild after code changes
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Execute commands in containers
docker-compose -f docker-compose.prod.yml exec web <command>
docker-compose -f docker-compose.prod.yml exec db <command>
```

## Files to Keep
- Keep: `.git/`, `media/`, all configuration files
- Exclude: `__pycache__/`, `*.pyc`, `inv_venv/`, `.env` (if contains secrets)

## Architecture
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│   Nginx     │ Port 80
└──────┬──────┘
       │ Proxy
       ▼
┌─────────────┐
│   Django    │ Port 8000
│  (Gunicorn) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    MySQL    │ Port 3306
└─────────────┘
```

## Support
For issues, check logs first:
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

