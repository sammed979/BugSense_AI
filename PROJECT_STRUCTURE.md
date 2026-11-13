# BugSense AI - Complete Project Structure

## Root Directory

```
BugSense_AI/
├── .env.example                          # Environment variables template
├── .gitignore                            # Git ignore rules
├── DEPLOYMENT_GUIDE.md                   # Deployment documentation
├── docker-compose.yml                    # Docker compose configuration
├── FINAL_IMPLEMENTATION_SUMMARY.md       # Final implementation summary
├── IMPLEMENTATION_SUMMARY.md             # Implementation summary
├── PROJECT_AUDIT.md                      # Project audit documentation
├── PROJECT_UPGRADE_DELIVERY_REPORT.md    # Delivery report
├── PROJECT_UPGRADE_DELIVERY_REPORT_UPDATED.md  # Updated delivery report
├── README.md                             # Project README
├── .vscode/                              # VS Code settings
│   └── settings.json
├── backend/                              # Django backend application
├── docker/                               # Docker configurations
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docs/                                 # Documentation
│   └── SETUP.md
├── execution-service/                   # Execution service (placeholder)
├── frontend/                             # Vanilla JS frontend
├── local-agent/                          # Local agent (placeholder)
└── _quarantine/                          # Quarantined files
```

## Backend Structure

```
backend/
├── .env                                  # Backend environment variables
├── .env.example                          # Backend environment template
├── db.sqlite3                            # SQLite database
├── manage.py                             # Django management script
├── requirements.txt                      # Python dependencies
├── .venv/                                # Python virtual environment (ignored)
│
├── apps/                                 # Django applications
│   ├── __init__.py
│   │
│   ├── accounts/                         # User authentication
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # User, AIProviderSettings models
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── migrations/                   # Database migrations
│   │       ├── 0001_initial.py
│   │       ├── 0002_alter_aiprovidersettings_*.py
│   │       └── __init__.py
│   │
│   ├── analysis/                         # Code analysis & LogSense
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── logsense_views.py             # Log analysis views
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                      # Analysis endpoints
│   │
│   ├── dashboard/                        # Dashboard & core models
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # Project, ProjectFile, DebuggingSession, etc.
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── migrations/                   # Database migrations
│   │       ├── 0001_initial.py
│   │       ├── 0002_projectfile_*.py
│   │       ├── 0003_projectanalysis_*.py
│   │       ├── 0004_projectissue_*.py
│   │       └── __init__.py
│   │
│   ├── execution/                        # Code execution
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                      # Execution endpoints
│   │
│   ├── history/                          # Session history
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── learning/                         # Learning/lessons
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # LearningTopic, Lesson models
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── migrations/                   # Database migrations
│   │       ├── 0001_initial.py
│   │       ├── 0002_builtin_lessons.py
│   │       ├── 0003_alter_learningtopic_*.py
│   │       ├── 0004_learningtopic_*.py
│   │       ├── 0005_debugging_curriculum.py
│   │       ├── 0006_add_backend_http_lessons.py
│   │       ├── 0007_expand_error_catalogue.py
│   │       ├── 0008_restore_legacy_lessons.py
│   │       └── __init__.py
│   │
│   ├── projects/                         # Project management
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # Delegates to dashboard models
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   ├── views.py                      # Project CRUD, upload, analysis
│   │   └── management/
│   │       └── commands/
│   │           ├── cleanup_workspaces.py  # Django management command
│   │           └── __init__.py
│   │
│   ├── repair/                           # Code repair
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py                      # Repair endpoints
│   │
│   └── verification/                     # Code verification
│       ├── admin.py
│       ├── apps.py
│       ├── models.py
│       ├── urls.py
│       └── views.py                      # Verification endpoints
│
├── config/                               # Django configuration
│   ├── asgi.py                           # ASGI config
│   ├── settings.py                       # Django settings
│   ├── urls.py                           # Root URL configuration
│   ├── wsgi.py                           # WSGI config
│   └── __init__.py
│
├── sandbox/                              # Code execution sandbox
│   ├── python_runner.py                  # Python code runner
│   └── __pycache__/
│
├── services/                             # Business logic services
│   ├── ai_service.py                     # AI provider integration (OpenAI, Gemini)
│   ├── analysis_cache.py                 # Analysis caching
│   ├── code_analyzer.py                  # Static code analysis (AST, Ruff)
│   ├── error_parser.py                   # Error/traceback parsing
│   ├── local_repair_engine.py            # Heuristic repair engine
│   ├── log_sense.py                      # Log analysis
│   ├── project_ai_service.py             # Project-level AI analysis
│   ├── project_discovery_service.py      # Project structure discovery
│   ├── project_upload_service.py         # Secure file upload handling
│   ├── provider_router.py                # AI provider routing
│   ├── repair_engine.py                  # AI-powered repair
│   ├── static_analysis_service.py        # Project static analysis
│   ├── verification_engine.py           # Repair verification
│   └── __init__.py
│
├── static/                               # Static files
│   ├── css/
│   │   └── base.css
│   └── js/
│       ├── api.js
│       ├── auth.js
│       ├── dashboard.js
│       ├── history.js
│       ├── learning.js
│       ├── profile.js
│       ├── projects.js
│       └── workspace.js
│
├── templates/                            # Django templates
│   ├── base.html
│   ├── dashboard.html
│   ├── history.html
│   ├── landing.html
│   ├── learning.html
│   ├── login.html
│   ├── profile.html
│   ├── projects.html
│   ├── register.html
│   └── workspace.html
│
└── tests/                                # Backend tests
    ├── test_ai_provider_selection.py
    ├── test_code_analyzer.py
    ├── test_logsense.py
    ├── test_new_provider_flow.py
    └── __init__.py
```

## Frontend Structure

```
frontend/
├── dev-server.js                         # Development server
├── favicon.ico                           # Favicon
├── index.html                            # Main HTML file
├── package.json                          # Node.js dependencies
├── runtime-config.js                     # Runtime configuration
│
├── assets/                               # Static assets
│   ├── icons/
│   └── images/
│
├── css/                                  # Stylesheets
│   └── style.css                         # Main stylesheet (dark theme, responsive)
│
├── js/                                   # JavaScript modules
│   ├── api.js                            # API client (fetch, auth, endpoints)
│   ├── app.js                            # Main application (routing, UI rendering)
│   ├── auth.js                           # Authentication utilities
│   └── clipboard.js                      # Clipboard service
│
└── test/                                 # Frontend tests
    ├── api.test.js
    └── app-state.test.js
```

## Docker Structure

```
docker/
├── Dockerfile.backend                    # Backend Docker image
└── Dockerfile.frontend                   # Frontend Docker image
```

## Documentation Structure

```
docs/
└── SETUP.md                              # Setup documentation
```

## Quarantine Structure

```
_quarantine/                              # Unused/obsolete files (preserved)
├── history_views_template.py
├── learning_views_template2.py
├── projects_views_template2.py
├── REDESIGN_SUMMARY.md
├── REPAIR_WORKFLOW_FIX_REPORT.md
├── test_analysis.py
├── test_complete_workflow.py
├── test_complete_workflow_v2.py
├── test_login_error.py
├── test_register_error.py
├── test_repair.py
├── test_repair_workflow.py
├── test_verification.py
├── views_template.py
└── views_template2.py
```

## Key Technologies

### Backend
- **Framework**: Django 5.x
- **API**: Django REST Framework
- **Auth**: Simple JWT
- **Database**: SQLite (local), PostgreSQL (production)
- **AI Providers**: OpenAI, Google Gemini
- **Static Analysis**: Python AST, Ruff
- **Execution**: Isolated Python runner

### Frontend
- **Framework**: Vanilla JavaScript (ES6+)
- **Build**: Custom dev server
- **Editor**: Monaco Editor
- **API**: Fetch API
- **Routing**: Hash-based routing
- **Theme**: Dark mode (glassmorphism design)

## API Endpoints

### Authentication
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/token/refresh/` - Refresh access token
- `GET /api/v1/auth/me/` - Get user profile
- `PATCH /api/v1/auth/me/` - Update user profile

### Analysis
- `GET /api/v1/analysis/health/` - AI provider health check
- `POST /api/v1/analysis/` - Analyze code (static + AI)

### Execution
- `POST /api/v1/execution/` - Execute code

### Repair
- `POST /api/v1/repair/generate/` - Generate repair
- `POST /api/v1/repair/apply/` - Apply repair
- `POST /api/v1/repair/reject/` - Reject repair

### Verification
- `POST /api/v1/verification/` - Verify repair

### Projects
- `GET /api/v1/projects/` - List projects
- `POST /api/v1/projects/` - Create project
- `POST /api/v1/projects/upload/` - Upload ZIP project
- `POST /api/v1/projects/upload/single/` - Upload single file
- `POST /api/v1/projects/upload/multiple/` - Upload multiple files
- `GET /api/v1/projects/{id}/` - Get project details
- `DELETE /api/v1/projects/{id}/` - Delete project
- `GET /api/v1/projects/{id}/files/` - List project files
- `PUT /api/v1/projects/{id}/files/` - Save project file
- `POST /api/v1/projects/{id}/analyze/` - Analyze project
- `GET /api/v1/projects/{id}/analysis/` - Get project analysis
- `GET /api/v1/projects/{id}/issues/` - Get project issues
- `POST /api/v1/projects/{id}/repair/generate/` - Generate project repair
- `POST /api/v1/projects/{id}/repair/apply/` - Apply project repair
- `POST /api/v1/projects/{id}/repair/reject/` - Reject project repair
- `POST /api/v1/projects/{id}/repair/rollback/` - Rollback project repair
- `GET /api/v1/projects/{id}/download/` - Download repaired project

### Learning
- `GET /api/v1/learning/` - List lessons
- `GET /api/v1/learning/{id}/` - Get lesson details
- `POST /api/v1/learning/recommendations/` - Get lesson recommendations

### History
- `GET /api/v1/history/` - List sessions
- `GET /api/v1/history/{id}/` - Get session details

## Database Models

### Core Models (dashboard)
- `User` - Extended user model
- `AIProviderSettings` - User AI provider preferences
- `Project` - Project metadata
- `ProjectFile` - Project file content
- `DebuggingSession` - Debugging session
- `AnalysisResult` - Analysis results
- `RepairAttempt` - Repair attempts
- `VerificationRun` - Verification runs
- `FileChange` - File change tracking
- `UserFeedback` - User feedback
- `ProjectAnalysis` - Project analysis metadata
- `ProjectIssue` - Project issues
- `SuggestedFix` - Suggested fixes
- `AppliedChange` - Applied changes

### Learning Models
- `LearningTopic` - Learning topics
- `Lesson` - Debugging lessons

## Environment Variables

### Backend (.env)
```
DJANGO_SECRET_KEY=django-insecure-dev-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EXECUTION_ENABLED=True
EXECUTION_TIMEOUT_SECONDS=5
EXECUTION_MEMORY_LIMIT_MB=128
EXECUTION_MAX_OUTPUT_BYTES=65536
REPAIR_MAX_ATTEMPTS=3
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.8-flash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
AI_PROVIDER_PRIORITY=gemini,openai,heuristic
```

## Running the Application

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Access
- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8000/api/v1
- Django Admin: http://127.0.0.1:8000/admin
