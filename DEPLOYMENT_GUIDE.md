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
- Multi-language execution toolchains: `gcc`, `g++`, `javac`/`java` (JDK 17+), and `node` (see below)

### Multi-Language Execution Toolchains

The workspace detects Python, Java, C, C++, and JavaScript and runs the code with
the matching toolchain. Install every toolchain on the host or the analysis and
execution endpoints degrade to `blocked` for the missing language.

Ubuntu / Debian:

```bash
sudo apt-get update && sudo apt-get install -y \
    build-essential default-jdk nodejs
```

macOS (Homebrew):

```bash
brew install gcc openjdk node
```

**Render (native runtime):** set the service Build Command so the toolchains are
present before the app boots:

```bash
apt-get update && apt-get install -y build-essential default-jdk nodejs && pip install -r backend/requirements.txt
```

Keep the Start Command / Procfile unchanged:
`python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120`

`gcc`/`g++` and `node` are found automatically via `PATH`; `javac`/`java` come from
`default-jdk`. If a toolchain is absent, the verification step reports the language
as `blocked` instead of failing the request.

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

# Local development: omit DATABASE_URL to use SQLite with DEBUG=True.
# Render production: DATABASE_URL must be the attached PostgreSQL database URL.
# Never commit DATABASE_URL or print it in logs.

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
With `DEBUG=True` and no `DATABASE_URL`, SQLite is used for local development.

### Production (PostgreSQL)

1. Attach the Render PostgreSQL database to the backend service and ensure Render
   provides its `DATABASE_URL` environment variable.
2. The Django settings parse `DATABASE_URL` with `dj-database-url` and require
   PostgreSQL on Render. The app fails to start rather than silently using SQLite
   when a Render database URL is missing or is not PostgreSQL.
3. Configure the Render Pre-Deploy Command as
   `python manage.py migrate_locked --noinput && python manage.py database_diagnostics`.
   If Pre-Deploy is unavailable, use the migration and diagnostic commands before
   Gunicorn in the Start Command.

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
python manage.py migrate_locked --noinput && python manage.py database_diagnostics && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
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
