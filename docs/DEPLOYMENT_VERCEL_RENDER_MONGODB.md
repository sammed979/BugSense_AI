# BugSense AI - Deployment Guide

This guide explains how to deploy BugSense AI to production using:
- **Vercel** for the frontend
- **Render** for the Django backend
- **MongoDB Atlas** for the database

## Prerequisites

1. A GitHub repository with your BugSense AI code
2. MongoDB Atlas account (free tier available)
3. Render account (free tier available)
4. Vercel account (free tier available)

## Architecture

```
┌─────────────────┐
│   Vercel        │
│   Frontend      │
│   (Static)      │
└────────┬────────┘
         │
         │ HTTPS
         │
┌────────▼────────┐
│   Render        │
│   Backend       │
│   (Django)      │
└────────┬────────┘
         │
         │ MongoDB
         │
┌────────▼────────┐
│   MongoDB Atlas │
│   Database      │
└─────────────────┘
```

## Step 1: Set Up MongoDB Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free account (if you don't have one)
3. Create a new cluster:
   - Select "Free" tier
   - Choose a region close to your users
   - Click "Create Cluster"
4. Create a database user:
   - Go to "Database Access"
   - Click "Create New User"
   - Set username and password (save these!)
   - Set "Built-in Role" to "Read and write to any database"
5. Configure network access:
   - Go to "Network Access"
   - Click "Add IP Address"
   - Select "Allow Access from Anywhere" (0.0.0.0/0)
6. Get your connection string:
   - Go to "Database" → "Connect"
   - Select "Connect your application"
   - Copy the connection string (save this!)

Your connection string will look like:
```
mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/bugsense?retryWrites=true&w=majority
```

## Step 2: Deploy Backend to Render

1. **Push your code to GitHub** (if not already done)
2. Go to [Render](https://render.com)
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Configure the web service:
   - **Name**: `bugsense-ai-backend`
   - **Branch**: `master`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120`
6. Add environment variables (click "Advanced" → "Add Environment Variable"):
   ```
   DJANGO_SECRET_KEY=<generate-a-random-key>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=*.onrender.com
   DATABASE_ENGINE=mongodb
   MONGO_URI=<your-mongodb-connection-string>
   MONGO_DB_NAME=bugsense
   FRONTEND_URL=https://your-frontend-url.vercel.app
   CORS_ALLOWED_ORIGINS=https://your-frontend-url.vercel.app
   CORS_ALLOW_ALL_ORIGINS=False
   EXECUTION_ENABLED=True
   EXECUTION_TIMEOUT_SECONDS=5
   EXECUTION_MEMORY_LIMIT_MB=128
   EXECUTION_MAX_OUTPUT_BYTES=65536
   REPAIR_MAX_ATTEMPTS=3
   GEMINI_API_KEY=<your-gemini-api-key>
   GEMINI_MODEL=gemini-2.5-flash
   OPENAI_API_KEY=<your-openai-api-key>
   OPENAI_MODEL=gpt-4o
   AI_PROVIDER_PRIORITY=gemini,openai,heuristic
   ```
7. Click "Create Web Service"
8. Wait for deployment (first deployment takes ~5-10 minutes)
9. Copy your backend URL (e.g., `https://bugsense-ai-backend.onrender.com`)

**Important**: Run migrations after first deployment:
- Go to Render dashboard
- Click "Manual Deploy" → "Deploy latest commit"
- Add to "Build Command": `pip install -r requirements.txt && python manage.py migrate`
- Or use Render shell to run migrations

## Step 3: Deploy Frontend to Vercel

1. Go to [Vercel](https://vercel.com)
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Configure the project:
   - **Framework Preset**: Other
   - **Root Directory**: `frontend`
   - **Build Command**: (leave empty - static files)
   - **Output Directory**: (leave empty - root directory)
5. Add environment variables:
   - Click "Environment Variables"
   - Add: `RENDER_BACKEND_URL` = `https://your-backend.onrender.com`
6. Click "Deploy"
7. Wait for deployment (~1-2 minutes)
8. Copy your frontend URL (e.g., `https://bugsense-ai.vercel.app`)

## Step 4: Update CORS Configuration

1. Go back to Render
2. Edit your backend service
3. Update environment variables:
   - `FRONTEND_URL` = your actual Vercel URL
   - `CORS_ALLOWED_ORIGINS` = your actual Vercel URL
4. Click "Save Changes"
5. Trigger a new deployment

## Step 5: Update Frontend API URL

Option 1: Update in Vercel
1. Go to Vercel dashboard
2. Edit your project
3. Add environment variable: `RENDER_BACKEND_URL` = your Render backend URL
4. Redeploy

Option 2: Update in code
1. Edit `frontend/js/api.js`
2. Replace `https://your-backend.onrender.com` with your actual backend URL
3. Commit and push to GitHub
4. Vercel will auto-deploy

## Step 6: Run Migrations

Since you're using MongoDB with Djongo, migrations work differently:

1. **For local development** (SQLite):
   ```bash
   cd backend
   python manage.py migrate
   ```

2. **For production** (MongoDB):
   - Djongo automatically creates collections
   - No traditional migrations needed
   - Models are mapped to MongoDB collections automatically

However, if you have existing SQLite data:
1. Export your SQLite data
2. Import to MongoDB (optional, for production use)
3. Or start fresh with MongoDB

## Environment Variables Reference

### Backend (Render)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Yes | Django secret key | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_DEBUG` | Yes | Debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | Yes | Allowed hosts | `*.onrender.com` |
| `DATABASE_ENGINE` | Yes | Database type | `mongodb` |
| `MONGO_URI` | Yes | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/bugsense` |
| `MONGO_DB_NAME` | Yes | Database name | `bugsense` |
| `FRONTEND_URL` | Yes | Frontend URL for CORS | `https://bugsense.vercel.app` |
| `CORS_ALLOWED_ORIGINS` | Yes | CORS origins | `https://bugsense.vercel.app` |
| `CORS_ALLOW_ALL_ORIGINS` | Yes | Allow all origins | `False` |
| `EXECUTION_ENABLED` | No | Enable code execution | `True` |
| `GEMINI_API_KEY` | No | Google Gemini API key | `AIza...` |
| `GEMINI_MODEL` | No | Gemini model | `gemini-2.5-flash` |
| `OPENAI_API_KEY` | No | OpenAI API key | `sk-...` |
| `OPENAI_MODEL` | No | OpenAI model | `gpt-4o` |
| `AI_PROVIDER_PRIORITY` | No | Provider priority | `gemini,openai,heuristic` |

### Frontend (Vercel)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `RENDER_BACKEND_URL` | Yes | Backend API URL | `https://bugsense-ai-backend.onrender.com` |

## Troubleshooting

### Backend Won't Start
- Check Render logs
- Verify MongoDB connection string
- Check environment variables
- Ensure database is accessible

### CORS Errors
- Verify `FRONTEND_URL` matches actual Vercel URL
- Check `CORS_ALLOWED_ORIGINS` includes frontend URL
- Restart backend after changing CORS settings

### Database Connection Failed
- Verify MongoDB cluster is running
- Check IP whitelist (0.0.0.0/0)
- Verify username/password
- Check connection string format

### Frontend Can't Connect to Backend
- Verify backend URL is correct
- Check backend is running
- Verify CORS configuration
- Check browser console for errors

### MongoDB Issues with Djongo
- Djongo is not a production-grade MongoDB adapter
- Consider using `mongoengine` or `pymongo` directly for production
- For production, consider PostgreSQL instead of MongoDB

## Alternative: Use PostgreSQL Instead of MongoDB

For better Django compatibility, consider using PostgreSQL:

1. Set up PostgreSQL on Render:
   - Create a PostgreSQL database on Render
   - Get the connection string

2. Update backend environment variables:
   ```
   DATABASE_ENGINE=postgresql
   DB_NAME=<your-db-name>
   DB_USER=<your-db-user>
   DB_PASSWORD=<your-db-password>
   DB_HOST=<your-db-host>
   DB_PORT=5432
   ```

3. Remove MongoDB dependencies from `requirements.txt`:
   ```
   # djongo==1.3.6
   # pymongo==4.6.1
   # dnspython==2.4.2
   ```
   Add instead:
   ```
   psycopg2-binary==2.9.9
   ```

4. Run migrations on Render:
   ```
   python manage.py migrate
   ```

## Cost Estimation

### Free Tier Limits (as of 2024)

**MongoDB Atlas Free:**
- 512 MB storage
- Shared RAM
- Good for development/small projects

**Render Free:**
- 512 MB RAM
- 750 hours/month
- Sleeps after 15 min inactivity
- Wakes up on request (takes ~30s)

**Vercel Free:**
- Unlimited bandwidth
- 100 GB-hours/month
- 50ms execution timeout
- Good for static sites

### Estimated Monthly Costs (if needed)

- MongoDB Atlas: $0 (free) to $9 (shared)
- Render: $0 (free) to $7 (starter)
- Vercel: $0 (free) to $20 (pro)

**Total**: $0 to $36/month

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong Django secret key
- [ ] Enable HTTPS (automatic on Vercel/Render)
- [ ] Set `DJANGO_DEBUG=False` in production
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets
- [ ] Rotate API keys regularly
- [ ] Enable MongoDB authentication
- [ ] Restrict MongoDB IP access (if possible)
- [ ] Monitor logs for suspicious activity

## Performance Optimization

1. **Backend (Render)**
   - Enable caching (Redis recommended)
   - Use CDN for static files
   - Optimize database queries
   - Enable gzip compression

2. **Frontend (Vercel)**
   - Enable Edge caching
   - Optimize images
   - Minify CSS/JS
   - Use lazy loading

3. **Database (MongoDB)**
   - Create indexes
   - Use connection pooling
   - Monitor query performance
   - Consider read replicas

## Monitoring

- **Render Logs**: Dashboard → Logs
- **Vercel Analytics**: Dashboard → Analytics
- **MongoDB Atlas**: Dashboard → Metrics
- **Error Tracking**: Consider Sentry or similar

## Backup Strategy

1. **MongoDB Atlas**
   - Automatic backups (paid tiers)
   - Manual snapshots
   - Export data regularly

2. **Code**
   - GitHub repository
   - Regular commits
   - Tag releases

3. **Configuration**
   - Document environment variables
   - Keep .env.example updated
   - Version control configuration

## Rollback Procedure

1. **Backend**
   - Go to Render dashboard
   - Click "Deployments"
   - Select previous deployment
   - Click "Redeploy"

2. **Frontend**
   - Go to Vercel dashboard
   - Click "Deployments"
   - Click "..." on previous deployment
   - Select "Promote to Production"

## Support

- **Render**: https://render.com/docs
- **Vercel**: https://vercel.com/docs
- **MongoDB Atlas**: https://docs.atlas.mongodb.com
- **Django**: https://docs.djangoproject.com

## Next Steps

1. Test the deployed application
2. Set up monitoring and alerts
3. Configure custom domains (optional)
4. Set up CI/CD pipeline
5. Document API endpoints
6. Create user documentation
