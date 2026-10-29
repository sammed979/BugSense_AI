# Setup Guide for BugSense AI

## Quick Start

### Backend Setup

1. **Navigate to the backend directory:**
```bash
cd backend
```

2. **Create a virtual environment:**

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `DJANGO_SECRET_KEY` - Generate a strong random key
- `EXECUTION_ENABLED=True` - To enable code execution (optional)

5. **Run database migrations:**
```bash
python manage.py migrate
```

6. **Create a superuser (optional):**
```bash
python manage.py createsuperuser
```

7. **Start the Django development server:**
```bash
python manage.py runserver
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

The frontend files (HTML, CSS, JavaScript) are already in the `frontend/` directory. Django will serve these as static files once properly configured.

To ensure static files are served correctly, run:
```bash
python manage.py collectstatic
```

This will copy static files to the `staticfiles/` directory.

### Access the Application

- **Main Application:** `http://localhost:8000`
- **Admin Panel:** `http://localhost:8000/admin`
- **API Endpoints:** `http://localhost:8000/api/v1/`

## Configuration Options

### Required

- `DJANGO_SECRET_KEY`: Django secret key for cryptographic signing

### Optional

- `DJANGO_DEBUG`: Enable/disable debug mode (default: True)
- `DJANGO_ALLOWED_HOSTS`: Comma-separated list of allowed hosts (default: localhost,127.0.0.1)
- `EXECUTION_ENABLED`: Enable code execution (default: False)
- `AI_PROVIDER`: AI provider (openai, anthropic, etc.)
- `AI_API_KEY`: API key for AI provider
- `AI_MODEL`: AI model to use
- `AI_BASE_URL`: Base URL for AI API

### Database Configuration

**Default (SQLite):**
No configuration needed. Django will create `db.sqlite3` automatically.

**PostgreSQL (Production):**
Uncomment and configure in `.env`:
```
DB_NAME=bugsense
DB_USER=bugsense
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Then update `DATABASES` in `backend/config/settings.py`.

## Testing Code Execution

1. Register and login to the application
2. Navigate to Workspace
3. Click "Load Example" to load broken code
4. Click "Run Code" to execute
5. View the error in the terminal

Note: Code execution requires `EXECUTION_ENABLED=True` in the backend `.env` file.

## AI Integration

To enable AI-powered analysis and repair:

1. Set AI provider configuration in `.env`:
```
AI_PROVIDER=openai
AI_API_KEY=your-api-key
AI_MODEL=gpt-4
```

2. Supported providers:
- `openai`
- `anthropic`

## Troubleshooting

### Port Already in Use
If port 8000 is already in use:
```bash
python manage.py runserver 8001
```

### Static Files Not Loading
Run collectstatic:
```bash
python manage.py collectstatic
```

### Database Errors
Delete the database file and run migrations again:
```bash
rm db.sqlite3
python manage.py migrate
```

### Import Errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Development Notes

- The frontend uses vanilla JavaScript with hash-based routing
- Django serves the frontend as a single-page application
- API endpoints are protected with JWT authentication
- Code execution is disabled by default for security
