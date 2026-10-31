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
- `GEMINI_API_KEY` - Optional; keep this key in `backend/.env`, never in frontend files
- `GEMINI_MODEL` - Defaults to `gemini-2.5-flash`; choose a model enabled for this key
- `AI_PROVIDER_PRIORITY=gemini` - Selects Gemini as the only default provider

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
python manage.py runserver 127.0.0.1:8000
```

The backend will be available at `http://127.0.0.1:8000`. Leave this terminal open while using the frontend.

### Frontend Setup

In a second terminal, run the static frontend server:
```powershell
cd frontend
npm run dev
```

Then open `http://127.0.0.1:5173`. It uses Node's built-in HTTP server and does not require `npm install`. Keep Django running separately on `127.0.0.1:8000` for the API.

The API URL defaults to the Django server above. To override it, start the Node server with `VITE_API_BASE_URL`, for example in PowerShell:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
npm run dev
```

### Access the Application

- **Main Application:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
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

To enable AI-powered analysis and repair, configure credentials only in `backend/.env`:

```env
GEMINI_API_KEY=your-google-ai-studio-key
GEMINI_MODEL=gemini-2.5-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
AI_PROVIDER_PRIORITY=gemini
```

User provider selection is saved through `/api/v1/auth/ai-provider/`. OpenAI is used only when selected or enabled as an explicit Automatic Fallback secondary provider. Keys are never entered in the browser. LogSense pattern explanations work locally; external interpretation requires the workspace consent control and redacts detected credentials before sending.

Provider quotas are controlled by Google/OpenAI. An exhausted quota is returned as a provider error; the app cannot add credits or mark a failed AI operation as successful.

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
Do not delete `db.sqlite3` if it contains user data. Back it up, inspect the migration status, and apply additive migrations:
```bash
python manage.py showmigrations
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
