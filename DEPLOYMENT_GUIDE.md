# BugSense AI - Deployment Guide

**Last Updated:** 2026-11-13

---

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Node.js 16+ (for frontend static server)
- SQLite (development) or PostgreSQL (production)
- 2GB RAM minimum, 4GB recommended
- 10GB disk space minimum

### Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Node.js Dependencies
```bash
cd frontend
npm install
```

---

## Environment Configuration

### Backend Environment Variables (.env)

Create `backend/.env`:

```env
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,localhost

# Database (SQLite for development, PostgreSQL for production)
# SQLite (default - no configuration needed)
# PostgreSQL (uncomment and configure):
# DB_NAME=bugsense
# DB_USER=bugsense
# DB_PASSWORD=your-password
# DB_HOST=localhost
# DB_PORT=5432

# AI Provider Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash

# Execution Limits
EXECUTION_ENABLED=True
EXECUTION_TIMEOUT_SECONDS=5
EXECUTION_MEMORY_LIMIT_MB=128
EXECUTION_MAX_OUTPUT_BYTES=65536

# Repair Settings
REPAIR_MAX_ATTEMPTS=3
```

### Frontend Configuration

`frontend/runtime-config.js`:

```javascript
window.BugSenseConfig = {
    API_BASE_URL: 'https://yourdomain.com/api/v1',
    ENVIRONMENT: 'production',
    VERSION: '1.0.0'
};
```

---

## Database Setup

### Development (SQLite)
SQLite is configured by default. No additional setup needed.

### Production (PostgreSQL)

1. Create database:
```sql
CREATE DATABASE bugsense;
CREATE USER bugsense WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE bugsense TO bugsense;
```

2. Update `backend/.env` with PostgreSQL credentials

3. Update `backend/config/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'bugsense'),
        'USER': os.environ.get('DB_USER', 'bugsense'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

4. Run migrations:
```bash
cd backend
python manage.py migrate
```

---

## Migration Steps

### 1. Apply Database Migrations
```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Superuser
```bash
python manage.py createsuperuser
```

### 3. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

---

## Running the Application

### Development Mode

**Backend:**
```bash
cd backend
python manage.py runserver 0.0.0.0:8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Access at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/v1
- Django Admin: http://localhost:8000/admin

### Production Mode

**Using Gunicorn (recommended):**

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run Gunicorn:
```bash
cd backend
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

**Using Nginx:**

Nginx configuration example:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/backend/staticfiles/;
    }

    location /media/ {
        alias /path/to/backend/media/;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /path/to/frontend;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## Maintenance Tasks

### Workspace Cleanup

Clean up expired project workspaces (older than 7 days):

```bash
cd backend
python manage.py cleanup_workspaces --days=7
```

Dry run first:
```bash
python manage.py cleanup_workspaces --days=7 --dry-run
```

### Database Backups

SQLite:
```bash
cp backend/db.sqlite3 backup/db.sqlite3.$(date +%Y%m%d)
```

PostgreSQL:
```bash
pg_dump bugsense > backup/bugsense_$(date +%Y%m%d).sql
```

### Cache Clearing

The in-memory cache is cleared automatically on server restart. No manual cache clearing needed.

---

## Security Checklist

### Before Production Deployment

- [ ] Change `DJANGO_SECRET_KEY` to a secure random value
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure `DJANGO_ALLOWED_HOSTS` to your domain
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure HTTPS/TLS (use Let's Encrypt or similar)
- [ ] Set up firewall rules (only allow ports 80, 443)
- [ ] Configure CORS for your frontend domain
- [ ] Rotate API keys regularly
- [ ] Set up workspace cleanup cron job
- [ ] Enable Django Admin protection
- [ ] Configure proper file permissions on media directory

### API Key Security

- Never commit `.env` file
- Use environment variables in production
- Rotate keys if exposed
- Monitor API usage for anomalies

---

## Performance Optimization

### Gunicorn Workers

Number of workers formula: `(2 * CPU_CORES) + 1`

Example for 4 cores:
```bash
gunicorn config.wsgi:application --workers 9
```

### Database Optimization

- Add indexes to frequently queried fields
- Use connection pooling (pgbouncer for PostgreSQL)
- Enable query logging in development only

### Static Files

- Use CDN for static assets in production
- Enable gzip compression in Nginx
- Set proper cache headers

---

## Monitoring

### Health Check Endpoint

Add to `backend/config/urls.py`:

```python
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'database': 'connected',
    })
```

### Logging

Configure logging in `backend/config/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/bugsense/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

---

## Troubleshooting

### Database Migration Errors

If migrations fail:
```bash
python manage.py migrate --fake-initial
python manage.py migrate
```

### Static Files Not Loading

```bash
python manage.py collectstatic --clear --noinput
```

### Permission Denied on Workspace Directory

```bash
chmod 755 backend/media/project_workspaces
```

### AI Provider Errors

- Check API keys in `.env`
- Verify API quota/billing
- Check network connectivity
- Review provider logs in Django admin

---

## Cron Jobs (Linux)

Add to crontab (`crontab -e`):

```cron
# Workspace cleanup - daily at 2 AM
0 2 * * * cd /path/to/backend && /path/to/venv/bin/python manage.py cleanup_workspaces --days=7

# Database backup - daily at 3 AM
0 3 * * * pg_dump bugsense > /path/to/backups/bugsense_$(date +\%Y\%m\%d).sql

# Restart Gunicorn - weekly on Sunday at 4 AM
0 4 * * 0 systemctl restart gunicorn
```

---

## Scaling Considerations

### Horizontal Scaling

- Use PostgreSQL with connection pooling
- Use Redis for session storage (if needed)
- Use load balancer (nginx, HAProxy)
- Store media files on object storage (S3, MinIO)

### Vertical Scaling

- Increase RAM for analysis workloads
- Use SSD for database and workspace storage
- Increase CPU for static analysis performance

---

## Backup and Recovery

### Backup Strategy

1. **Daily:** Database backup
2. **Weekly:** Full project backup (code + media)
3. **Monthly:** Archive old backups

### Recovery Procedure

1. Restore database from backup
2. Restore code from git
3. Restore media files from backup
4. Run migrations (if needed)
5. Restart services

---

## Support

For issues or questions:
- Check Django logs: `/var/log/bugsense/django.log`
- Check application logs: application logs location
- Review error logs in Django Admin
- Check AI provider status pages

---

## Version History

- **v1.0.0** (2026-11-13): Initial deployment guide
  - Project upload and analysis features
  - AI integration
  - Repair workflow
  - Workspace cleanup
  - Caching support
