# BugSense AI - Complete Project Structure

## Overview

BugSense AI is an AI-assisted debugging platform that helps developers identify, analyze, and fix code errors. The system is organized into **six logical functional modules** for clear presentation and understanding:

1. **Accounts Management** - User authentication, registration, and AI provider settings
2. **Debugging Workspace** - Code editor, execution, and session management
3. **AI Analysis** - Static analysis, error diagnosis, and LogSense log analysis
4. **Project Management** - Project upload, file management, and project-level analysis
5. **Code Repair and Verification** - AI-powered repair generation and verification
6. **Learning Centre** - Interactive debugging lessons and learning resources

> **Note:** These six modules are logical groupings for presentation purposes. The actual Django backend follows standard Django conventions with apps organized under `backend/apps/`.

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
├── PROJECT_STRUCTURE.md                  # This file - project structure
├── README.md                             # Project README
├── .vscode/                              # VS Code settings
│   └── settings.json
├── backend/                              # Django backend application
├── docker/                               # Docker configurations
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docs/                                 # Documentation
│   ├── PROJECT_STRUCTURE.md              # This file (link or copy)
│   ├── SYSTEM_ARCHITECTURE.md            # System architecture documentation
│   └── USER_GUIDE.md                     # User guide documentation
├── execution-service/                   # Execution service (placeholder)
├── frontend/                             # Vanilla JS frontend
├── local-agent/                          # Local agent (placeholder)
└── _quarantine/                          # Quarantined files (preserved, not used)
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
├── apps/                                 # Django applications (following Django conventions)
│   ├── __init__.py
│   │
│   ├── accounts/                         # → MODULE 1: Accounts Management
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
│   ├── analysis/                         # → MODULE 3: AI Analysis
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── logsense_views.py             # LogSense log analysis
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                      # Analysis endpoints
│   │
│   ├── dashboard/                        # Core models used across modules
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
│   ├── execution/                        # → MODULE 2: Debugging Workspace
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                      # Code execution endpoints
│   │
│   ├── history/                          # → MODULE 2: Debugging Workspace
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py                      # Session history endpoints
│   │
│   ├── learning/                         # → MODULE 6: Learning Centre
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
│   ├── projects/                         # → MODULE 4: Project Management
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
│   ├── repair/                           # → MODULE 5: Code Repair and Verification
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py                      # Repair endpoints
│   │
│   └── verification/                     # → MODULE 5: Code Repair and Verification
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
├── sandbox/                              # → MODULE 2: Debugging Workspace
│   ├── python_runner.py                  # Isolated Python code execution
│   └── __pycache__/
│
├── services/                             # Business logic services (shared across modules)
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
├── static/                               # Static files served by Django
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
├── PROJECT_STRUCTURE.md                  # This file (link or copy)
├── SYSTEM_ARCHITECTURE.md                # System architecture documentation
└── USER_GUIDE.md                         # User guide documentation
```

## Six Logical Functional Modules

The BugSense AI system is organized into six logical modules for clear understanding and presentation:

### Module 1: Accounts Management
**Django Apps:** `accounts/`

**Purpose:** User authentication, registration, and AI provider configuration

**Key Features:**
- User registration and login
- JWT-based authentication
- AI provider settings (OpenAI, Gemini)
- User profile management
- Session management

**Key Models:**
- `User` (extended Django user)
- `AIProviderSettings` (provider preferences, API keys)

**Key Endpoints:**
- `POST /api/v1/auth/register/` - Register new user
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/token/refresh/` - Refresh access token
- `GET /api/v1/auth/me/` - Get user profile
- `PATCH /api/v1/auth/me/` - Update user profile

---

### Module 2: Debugging Workspace
**Django Apps:** `execution/`, `history/`, `sandbox/`

**Purpose:** Code editor, execution environment, and session history

**Key Features:**
- Monaco code editor integration
- Isolated Python code execution
- Execution output capture
- Session history tracking
- Error traceback display

**Key Models:**
- `DebuggingSession` (code, language, error, logs)
- Session history records

**Key Services:**
- `python_runner.py` - Isolated code execution
- Resource limits (timeout, memory, output size)

**Key Endpoints:**
- `POST /api/v1/execution/` - Execute code
- `GET /api/v1/history/` - List sessions
- `GET /api/v1/history/{id}/` - Get session details

---

### Module 3: AI Analysis
**Django Apps:** `analysis/`

**Purpose:** Static analysis, error diagnosis, and log analysis

**Key Features:**
- Static code analysis (Python AST, Ruff)
- AI-powered error diagnosis (OpenAI, Gemini)
- LogSense log analysis
- Traceback parsing
- Error context analysis

**Key Services:**
- `code_analyzer.py` - Static analysis (AST, undefined names, syntax errors)
- `error_parser.py` - Traceback parsing
- `log_sense.py` - Log analysis and redaction
- `ai_service.py` - AI provider integration

**Key Endpoints:**
- `GET /api/v1/analysis/health/` - AI provider health check
- `POST /api/v1/analysis/` - Analyze code (static + AI)

---

### Module 4: Project Management
**Django Apps:** `projects/`, `dashboard/` (models)

**Purpose:** Project upload, file management, and project-level analysis

**Key Features:**
- Single file upload
- Multiple file upload
- ZIP archive upload with secure extraction
- Project file tree navigation
- Project-level static analysis
- Project-level AI analysis
- Cross-file dependency analysis
- Workspace management

**Key Models:**
- `Project` - Project metadata
- `ProjectFile` - File content and path
- `ProjectAnalysis` - Analysis results
- `ProjectIssue` - Detected issues
- `SuggestedFix` - AI-generated fixes
- `AppliedChange` - Change tracking

**Key Services:**
- `project_upload_service.py` - Secure file upload handling
- `project_discovery_service.py` - Project structure discovery
- `static_analysis_service.py` - Project static analysis
- `project_ai_service.py` - Project AI analysis
- `analysis_cache.py` - Analysis caching

**Key Endpoints:**
- `GET /api/v1/projects/` - List projects
- `POST /api/v1/projects/` - Create project
- `POST /api/v1/projects/upload/` - Upload ZIP project
- `POST /api/v1/projects/upload/single/` - Upload single file
- `POST /api/v1/projects/upload/multiple/` - Upload multiple files
- `GET /api/v1/projects/{id}/files/` - List project files
- `PUT /api/v1/projects/{id}/files/` - Save project file
- `POST /api/v1/projects/{id}/analyze/` - Analyze project
- `GET /api/v1/projects/{id}/issues/` - Get project issues

---

### Module 5: Code Repair and Verification
**Django Apps:** `repair/`, `verification/`

**Purpose:** AI-powered repair generation and verification

**Key Features:**
- AI-generated code repairs
- Heuristic (local) repairs
- Diff generation and display
- Repair approval workflow
- Repair verification
- Rollback functionality
- Change history tracking

**Key Services:**
- `repair_engine.py` - AI-powered repair
- `local_repair_engine.py` - Heuristic repairs
- `verification_engine.py` - Repair verification

**Key Models:**
- `RepairAttempt` - Repair attempts tracking
- `VerificationRun` - Verification results
- `FileChange` - Change tracking
- `AppliedChange` - Applied changes

**Key Endpoints:**
- `POST /api/v1/repair/generate/` - Generate repair
- `POST /api/v1/repair/apply/` - Apply repair
- `POST /api/v1/repair/reject/` - Reject repair
- `POST /api/v1/verification/` - Verify repair
- `POST /api/v1/projects/{id}/repair/generate/` - Generate project repair
- `POST /api/v1/projects/{id}/repair/apply/` - Apply project repair
- `POST /api/v1/projects/{id}/repair/rollback/` - Rollback project repair

---

### Module 6: Learning Centre
**Django Apps:** `learning/`

**Purpose:** Interactive debugging lessons and learning resources

**Key Features:**
- Structured debugging curriculum
- Interactive lessons
- Error pattern practice
- Follow-up questions
- Learning recommendations
- Progress tracking

**Key Models:**
- `LearningTopic` - Learning topics/categories
- `Lesson` - Debugging lessons
- Built-in error catalogue

**Key Endpoints:**
- `GET /api/v1/learning/` - List lessons
- `GET /api/v1/learning/{id}/` - Get lesson details
- `POST /api/v1/learning/recommendations/` - Get lesson recommendations

---

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
