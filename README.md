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

For the complete project structure, see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).

The backend follows Django conventions with apps organized under `backend/apps/`:
- `accounts/` - User authentication
- `dashboard/` - Core models (Project, Session, etc.)
- `projects/` - Project management
- `analysis/` - Code analysis
- `execution/` - Code execution
- `history/` - Session history
- `repair/` - Code repair
- `verification/` - Repair verification
- `learning/` - Learning centre

The frontend is a vanilla JavaScript application in `frontend/` with no build step required.

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

## Documentation

For detailed information about the system, see the documentation in the `docs/` directory:

- **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** - Complete project structure and file organization
- **[SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)** - System architecture, technology stack, and design decisions
- **[USER_GUIDE.md](docs/USER_GUIDE.md)** - User guide for all six functional modules

## Features

### Six Functional Modules

BugSense AI is organized into six logical functional modules:

1. **Accounts Management** - User authentication, registration, and AI provider settings
2. **Debugging Workspace** - Code editor, execution, and session management
3. **AI Analysis** - Static analysis, error diagnosis, and LogSense log analysis
4. **Project Management** - Project upload, file management, and project-level analysis
5. **Code Repair and Verification** - AI-powered repair generation and verification
6. **Learning Centre** - Interactive debugging lessons and learning resources

### ✅ Implemented Features

**Accounts Management:**
- User registration and login with JWT authentication
- JWT token refresh with automatic rotation
- User profile management
- AI provider settings (OpenAI, Gemini)
- Per-user provider preferences

**Debugging Workspace:**
- Monaco Editor integration with syntax highlighting
- Isolated Python code execution (configurable)
- Execution output capture (stdout, stderr, exit code)
- Resource limits (timeout, memory, output size)
- Session history tracking
- Terminal panel with multiple tabs (Output, Errors, AI Analysis, Repair Diff, Verification)

**AI Analysis:**
- Static code analysis (Python AST, Ruff linter)
- Syntax error detection
- Undefined variable detection
- Error context analysis
- AI-powered error diagnosis (OpenAI, Gemini)
- Provider routing with fallback (Gemini → OpenAI → Heuristic)
- LogSense log analysis with sensitive data redaction
- Consent-gated external AI interpretation
- Traceback parsing and error classification

**Project Management:**
- Single file upload
- Multiple file upload
- ZIP archive upload with secure extraction
- ZIP path traversal protection
- Project file tree navigation
- File preview and editing
- Project-level static analysis
- Project-level AI analysis
- Cross-file dependency analysis
- Issue tracking with severity levels
- Workspace management
- Automatic workspace cleanup

**Code Repair and Verification:**
- AI-powered repair generation
- Heuristic (local) repair engine
- Diff generation and display
- Repair approval workflow (Apply/Reject)
- Repair verification (syntax check + execution test)
- Rollback functionality
- Change history tracking
- Repaired project ZIP download

**Learning Centre:**
- Structured debugging curriculum
- Interactive lessons with code examples
- Error pattern lessons (NameError, TypeError, etc.)
- Practice problems
- AI-powered lesson recommendations
- Progress tracking
- Follow-up questions
- Built-in error catalogue

### 🚧 Future Enhancements

- Real-time collaboration features
- Additional language support (JavaScript, Java, C++)
- Advanced project analysis patterns
- Custom AI model integration
- Plugin system architecture
- Team workspaces
- CI/CD integration

### Current Limitations

- AI availability depends on configured provider keys, model access, and quota
- Python execution uses a restricted subprocess (not Docker-grade production sandbox)
- LogSense local analysis uses explainable patterns; enable AI for complex logs
- Multi-language support beyond Python is not yet implemented
- Project analysis is optimized for Python projects

## Security Considerations

- Passwords are hashed using Django's default password hasher
- JWT tokens for authentication with automatic refresh
- User data isolation (each user can only access their own data)
- Code execution in restricted environment with resource limits
- No hardcoded secrets (API keys stored in environment variables)
- Input validation on both frontend and backend
- ZIP path traversal protection for file uploads
- File size limits and type validation
- CORS configuration for frontend-backend communication

## Support

For detailed information:
- **User Guide:** [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - How to use all six modules
- **System Architecture:** [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) - Technical design and architecture
- **Project Structure:** [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) - Complete file organization

For issues or questions, refer to the documentation in the `docs/` directory.
