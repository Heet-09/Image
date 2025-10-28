# Quick Start Guide - Deploying to New Server

## 🚀 Fast Deployment (5 Minutes)

### 1. Copy Files to Server
```bash
# Option A: Using Git
git clone <your-repo-url>
cd Image

# Option B: Using SCP
scp -r . user@new-server:/path/to/Image
```

### 2. Run This Command
```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment script
./deploy.sh

# OR manually:
docker-compose -f docker-compose.prod.yml up -d --build
```

### 3. Initialize Database
```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# (Optional) Collect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# (Optional) Create admin user
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 4. Done! ✅
Visit: **http://your-server-ip**

---

## 📋 Essential Commands

### Check Status
```bash
docker-compose -f docker-compose.prod.yml ps
```

### View Logs
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Restart Application
```bash
docker-compose -f docker-compose.prod.yml restart web
```

### Stop Application
```bash
docker-compose -f docker-compose.prod.yml down
```

### Start Application
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Rebuild After Updates
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 🔧 Configuration

### Change Passwords (IMPORTANT!)
Edit `docker-compose.prod.yml`:
```yaml
environment:
  MYSQL_PASSWORD: your_new_password
  MYSQL_ROOT_PASSWORD: your_new_root_password
```

Then restart:
```bash
docker-compose -f docker-compose.prod.yml restart db
```

---

## 🌐 Access Points

Once deployed, access:
- **Home**: http://your-server-ip/
- **Search**: http://your-server-ip/cbir/search/
- **Upload**: http://your-server-ip/cbir/upload/

---

## 🆘 Troubleshooting

### Container won't start?
```bash
docker-compose -f docker-compose.prod.yml logs
```

### Out of memory?
```bash
docker stats
```

### Database connection error?
```bash
docker-compose -f docker-compose.prod.yml restart db
```

### Need to reset everything?
```bash
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 📦 What Gets Deployed

- **Nginx**: Reverse proxy on port 80
- **Django Web**: Application on port 8000
- **MySQL**: Database on port 3306 (internal)

All connected via Docker Compose!

---

## 🔒 Security Checklist for Production

- [ ] Change default database passwords
- [ ] Set up SSL/HTTPS
- [ ] Configure firewall (port 80, 443)
- [ ] Set `DEBUG = False` in settings.py
- [ ] Configure ALLOWED_HOSTS in settings.py
- [ ] Set up regular backups
- [ ] Enable Docker logging
- [ ] Use secrets management

