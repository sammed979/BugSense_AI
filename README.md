# BugSense AI

AI-assisted debugging, repair review, verification, LogSense, and developer learning platform

## Overview

BugSense AI is a college Computer Science Engineering project for code debugging, user-approved repair proposals, verification, and technical log explanations. LogSense accepts standalone text logs, explains lines locally, and can request a redacted external AI interpretation only after explicit consent.

## Technology Stack

### Frontend
- **HTML5** - Page structure and semantic elements
- **CSS3** - Responsive layouts, animations, styling, themes
- **Vanilla JavaScript (ES6+)** - Interactions, form validation, API requests, dynamic updates
- **Monaco Editor** - Code editor with syntax highlighting (to be integrated)
- **Fetch API** - Communication with Django backend

### Backend
- **Python 3.11+**
- **Django 5.0** - Web framework
- **Django REST Framework** - REST API development
- **SQLite** - Database for development (PostgreSQL for production)
- **Django ORM** - Database operations
- **Python AST** - Source code analysis
- **Ruff** - Python linting and static checks
- **pytest** - Automated testing

### AI Integration
- Gemini and OpenAI adapters, per-user provider selection, and a deterministic local repair path
- LogSense local explanations with consent-gated external interpretation

## Project Structure

```
BugSense-AI/
│
├── frontend/              # Vanilla HTML/CSS/JS frontend
│   ├── index.html        # Main HTML file
│   ├── css/
│   │   └── style.css     # Main stylesheet
│   ├── js/
│   │   ├── api.js        # API client
│   │   ├── auth.js       # Authentication module
│   │   └── app.js        # Main application logic
│   └── assets/
│       ├── images/
│       └── icons/
│
├── backend/              # Django backend
│   ├── manage.py         # Django management script
│   ├── requirements.txt  # Python dependencies
│   ├── .env.example      # Environment variables template
│   ├── config/           # Django settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── apps/             # Django apps
│   │   ├── accounts/     # User authentication
│   │   ├── dashboard/    # Dashboard and statistics
│   │   ├── projects/     # Project management
│   │   ├── analysis/     # Code analysis
│   │   ├── repair/       # Automatic repair
│   │   ├── execution/    # Code execution
│   │   ├── verification/  # Repair verification
│   │   ├── history/      # Debugging history
│   │   └── learning/     # Learning centre
│   ├── services/         # Business logic services
│   │   ├── ai_service.py
│   │   ├── error_parser.py
│   │   ├── code_analyzer.py
│   │   ├── repair_engine.py
│   │   └── verification_engine.py
│   ├── sandbox/          # Code execution sandbox
│   │   └── python_runner.py
│   └── tests/            # Backend tests
│
├── docs/                 # Documentation
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:

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

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment example:
```bash
cp .env.example .env
```

5. Edit `.env` and set at minimum:
- `DJANGO_SECRET_KEY` - Generate a strong random key
- `EXECUTION_ENABLED=true` - To enable code execution

6. Apply additive database migrations (back up `db.sqlite3` before schema changes if it contains data):
```bash
python manage.py migrate
```

7. Create a superuser (optional, for admin access):
```bash
python manage.py createsuperuser
```

8. Start the Django development server:
```bash
python manage.py runserver
```

The backend will be available at `http://127.0.0.1:8000`. Leave this terminal open while using the frontend.

### Frontend Setup

The frontend is a static HTML/CSS/JavaScript app. Start it from a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. No npm packages need to be installed. Start the Django backend separately with `python manage.py runserver 127.0.0.1:8000` from `backend/`.

### Access the Application

- Application: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Admin Panel: `http://localhost:8000/admin`
- API Documentation: Django REST Framework browsable API at `http://localhost:8000/api/v1/`

## Environment Variables

See `backend/.env.example` for all available configuration options:

- `DJANGO_SECRET_KEY`: Required for Django security
- `DEBUG`: Enable/disable debug mode
- `EXECUTION_ENABLED`: Enable code execution (requires secure runner)
- `GEMINI_API_KEY` / `GEMINI_MODEL`: Optional Gemini credentials and model, backend only
- `OPENAI_API_KEY` / `OPENAI_MODEL`: Optional OpenAI credentials and model, backend only
- `AI_PROVIDER_PRIORITY`: Legacy provider default; per-user provider preferences are stored in Django
- `CORS_ALLOWED_ORIGINS`: Allowed CORS origins

## Features

### ✅ Implemented

- User registration and login with JWT authentication
- Dashboard with real database statistics
- Workspace with three diagnostic inputs (error message, terminal logs, source code)
- Dedicated LogSense page for pasted logs and `.txt` / `.log` uploads, with English/Kannada and three explanation levels
- Consent-gated, redacted external log interpretation and per-user saved explanation history
- LogSense practice activities saved to the user's Learning Centre history
- Code execution service (when enabled)
- Error analysis engine (traceback parsing, static analysis)
- AI integration for diagnosis and repair (when configured)
- Deterministic local repair engine and provider-routed repair proposals
- User-reviewed repair diffs and verification statuses that require actual execution to pass
- Django REST Framework APIs

### 🚧 To Be Implemented

- Monaco Editor integration (currently using textarea)
- Project upload functionality
- Approval and rollback workflow
- Local agent for file modifications
- Complete history and reports
- Learning centre content
- Automated backend and frontend regression tests

### Current limitations

- Local LogSense uses explainable patterns and may not understand an unfamiliar format; enable source-sharing consent for configured external AI interpretation.
- External AI availability depends on the configured provider key, model access, and quota.
- Python execution uses a restricted temporary subprocess and is disabled unless explicitly enabled. It is not a Docker-grade production sandbox.
- The existing application does not yet provide the full multi-file project explorer, rollbackable filesystem patching, reports, or a complete course catalog.

## Security Considerations

- Passwords are hashed using Django's default password hasher
- JWT tokens for authentication
- User data isolation (each user can only access their own data)
- Code execution in restricted environment (when enabled)
- No hardcoded secrets
- Input validation on both frontend and backend

## Limitations

- Python execution is disabled by default until configured
- Email verification requires SMTP configuration
- AI integration requires API key configuration
- Multi-language support (JavaScript, Java, C++) is not yet implemented
- Monaco Editor integration pending (using textarea as placeholder)

## Contributing

This is a student project. Contributions should align with the project goals and maintain code quality.

## License

This is an educational project developed for academic purposes.

## Support

For issues or questions, please refer to the documentation in the `docs/` directory.
