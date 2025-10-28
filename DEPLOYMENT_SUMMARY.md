# Deployment Summary - Quick Reference

## 📦 Files to Transfer to New Server

### Required Files:
```
cbir_app/              # Django application
cbir_project/          # Django settings
nginx/                 # Nginx configuration
docker-compose.prod.yml
Dockerfile
requirements.txt
manage.py
```

### Optional Files:
```
data/                  # If you have existing data
media/                 # If you have uploaded images
.gitignore
```

### Exclude:
```
__pycache__/          # Python cache
inv_venv/             # Virtual environment
.git/                  # Git repository (unless deploying via Git)
static/                # Auto-generated
```

---

## 🚀 Quick Deploy Steps

### Step 1: On Your New Server

```bash
# Install Docker (if not installed)
curl -fsSL https://get.docker.com | sh

# Install Docker Compose (if not installed)
pip install docker-compose
```

### Step 2: Transfer Files

**Option A: Using Git (Recommended)**
```bash
git clone <your-repo-url>
cd Image
```

**Option B: Using SCP**
```bash
# From your local machine, run:
scp -r cbir_app/ cbir_project/ nginx/ docker-compose.prod.yml Dockerfile requirements.txt manage.py user@new-server:/path/to/Image/
```

### Step 3: Configure

Edit `docker-compose.prod.yml` and change passwords:
```yaml
environment:
  MYSQL_PASSWORD: your_secure_password
  MYSQL_ROOT_PASSWORD: your_root_password
```

### Step 4: Deploy

```bash
cd Image

# Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# (Optional) Create admin user
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### Step 5: Verify

```bash
# Check containers are running
docker-compose -f docker-compose.prod.yml ps

# Should show: db, web, nginx all as "Up"
```

Visit: **http://your-server-ip**

---

## 🎯 One-Line Deploy (if using Git)

```bash
git clone <repo> && cd Image && docker-compose -f docker-compose.prod.yml up -d --build && docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

---

## 📋 Essential Commands Reference

```bash
# Start application
docker-compose -f docker-compose.prod.yml up -d

# Stop application
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart
docker-compose -f docker-compose.prod.yml restart

# Rebuild after code changes
docker-compose -f docker-compose.prod.yml up -d --build

# Check status
docker-compose -f docker-compose.prod.yml ps

# Access Django shell
docker-compose -f docker-compose.prod.yml exec web python manage.py shell

# Access database
docker-compose -f docker-compose.prod.yml exec db mysql -u root -p
```

---

## ⚙️ Configuration Files Summary

### 1. `docker-compose.prod.yml`
- Database credentials (CHANGE PASSWORDS!)
- Container configurations
- Port mappings

### 2. `nginx/nginx.conf`
- Upload size limit (50MB)
- Reverse proxy settings
- Static file serving

### 3. `cbir_project/settings.py`
- Django settings
- Database configuration
- File upload limits
- **Set ALLOWED_HOSTS for production**

### 4. `Dockerfile`
- Python version
- Dependencies
- Build commands

---

## 🌐 Architecture

```
Internet → Port 80 (Nginx) → Port 8000 (Django/Gunicorn) → Port 3306 (MySQL)
```

All running in Docker containers!

---

## 🔒 Production Security Checklist

- [ ] Change `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD`
- [ ] Set `DEBUG = False` in settings.py
- [ ] Set `ALLOWED_HOSTS = ['your-domain.com']` in settings.py
- [ ] Set up SSL/HTTPS certificates
- [ ] Configure firewall (allow port 80, 443)
- [ ] Set up automated backups
- [ ] Enable Docker logging
- [ ] Use environment variables for secrets
- [ ] Review file upload size limits (currently 50MB)

---

## 📞 Need Help?

Check logs:
```bash
docker-compose -f docker-compose.prod.yml logs
```

View detailed guide: See `DEPLOYMENT.md` and `QUICK_START.md`

