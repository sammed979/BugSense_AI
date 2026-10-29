# BugSense AI

AI-Powered Autonomous Code Debugging, Automatic Repair and Verification Platform

## Overview

BugSense AI is a college Computer Science Engineering mini-project that combines AI-powered code analysis with automatic program repair. The platform accepts error messages, terminal logs, and source code as inputs, analyzes the evidence, generates candidate corrections, executes them in a secure environment, and enables users to review and approve repairs.

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
- Provider-independent AI service (OpenAI, Anthropic, etc.)
- Configurable through environment variables

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
├── local-agent/          # Local file modification agent
├── execution-service/    # Docker-based execution service
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

6. Run database migrations:
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

The backend will be available at `http://localhost:8000`

### Frontend Setup

The frontend is served through Django's static files. The HTML, CSS, and JavaScript files are already in place in the `frontend/` directory.

To serve the frontend properly, ensure Django's static files are configured correctly in `backend/config/settings.py`.

### Access the Application

- Application: `http://localhost:8000`
- Admin Panel: `http://localhost:8000/admin`
- API Documentation: Django REST Framework browsable API at `http://localhost:8000/api/v1/`

## Environment Variables

See `backend/.env.example` for all available configuration options:

- `DJANGO_SECRET_KEY`: Required for Django security
- `DEBUG`: Enable/disable debug mode
- `EXECUTION_ENABLED`: Enable code execution (requires secure runner)
- `AI_PROVIDER`: AI provider (openai, anthropic, etc.)
- `AI_API_KEY`: API key for AI provider
- `CORS_ALLOWED_ORIGINS`: Allowed CORS origins

## Features

### ✅ Implemented

- User registration and login with JWT authentication
- Dashboard with real database statistics
- Workspace with three diagnostic inputs (error message, terminal logs, source code)
- Code execution service (when enabled)
- Error analysis engine (traceback parsing, static analysis)
- AI integration for diagnosis and repair (when configured)
- Automatic repair engine with verification
- Django REST Framework APIs

### 🚧 To Be Implemented

- Monaco Editor integration (currently using textarea)
- Project upload functionality
- Approval and rollback workflow
- Local agent for file modifications
- Complete history and reports
- Learning centre content
- Automated tests

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
