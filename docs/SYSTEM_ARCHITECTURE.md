# BugSense AI - System Architecture

## Overview

BugSense AI is an AI-assisted debugging platform that helps developers identify, analyze, and fix code errors. The system uses a modern Django backend with a vanilla JavaScript frontend, integrating multiple AI providers (OpenAI, Google Gemini) for intelligent code analysis and repair.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                            │
│                  (Vanilla JavaScript + Monaco)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Workspace   │  │  Projects    │  │  Learning    │        │
│  │  Editor      │  │  Explorer    │  │  Centre      │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                    HTTP/REST API
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                      Django Backend Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Accounts   │  │   Analysis   │  │   Repair     │        │
│  │   Module     │  │   Module     │  │   Module     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Workspace   │  │   Projects   │  │   Learning   │        │
│  │   Module     │  │   Module     │  │   Module     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                    Business Logic Layer
                            │
  ┌──────────────────────────────────────────────────────────┐  │
  │                    Services Layer                         │  │
  │  AI Service | Code Analyzer | Repair Engine | LogSense   │  │
  └──────────────────────────────────────────────────────────┘  │
                            │
                    External AI Providers
                            │
  ┌──────────────────────────────────────────────────────────┐  │
  │    OpenAI API         |         Google Gemini API          │  │
  └──────────────────────────────────────────────────────────┘  │
                            │
                    Data Layer
                            │
  ┌──────────────────────────────────────────────────────────┐  │
  │         SQLite (Development) | PostgreSQL (Production)     │  │
  └──────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Framework:** Django 5.x
- **API Framework:** Django REST Framework
- **Authentication:** Simple JWT
- **Database:** SQLite (local), PostgreSQL (production)
- **AI Providers:** OpenAI (GPT-4o), Google Gemini (gemini-3.8-flash)
- **Static Analysis:** Python AST, Ruff linter
- **Code Execution:** Isolated Python runner with resource limits

### Frontend
- **Framework:** Vanilla JavaScript (ES6+)
- **Code Editor:** Monaco Editor
- **API Communication:** Fetch API
- **Routing:** Hash-based routing
- **UI Theme:** Dark mode with glassmorphism design
- **Build Tool:** Custom development server

## System Components

### 1. Authentication Module (accounts/)

**Purpose:** User authentication and AI provider configuration

**Components:**
- **Models:**
  - `User`: Extended Django user model
  - `AIProviderSettings`: User's AI provider preferences (OpenAI, Gemini)

- **Views:**
  - User registration
  - User login/logout
  - Token refresh
  - Profile management
  - AI provider settings

- **Security:**
  - JWT-based authentication
  - Access token expiration
  - Refresh token rotation
  - Password hashing

**Data Flow:**
```
User → Register/Login → JWT Token → Frontend Storage → API Requests
```

---

### 2. Debugging Workspace Module (execution/, history/, sandbox/)

**Purpose:** Code editing, execution, and session management

**Components:**
- **Frontend:**
  - Monaco Editor integration
  - Code execution button
  - Output display terminal
  - Session history viewer

- **Backend:**
  - `python_runner.py`: Isolated code execution
  - Resource limits: 5s timeout, 128MB memory, 64KB output
  - Execution result capture (stdout, stderr, exit code)

- **Models:**
  - `DebuggingSession`: Stores code, language, error, logs
  - Session history tracking

**Data Flow:**
```
Editor → Execute Code → Python Runner → Result → Display Output
        ↓
    Save Session → Database → History List
```

**Security:**
- Isolated execution environment
- Resource limits prevent infinite loops
- No file system access
- No network access during execution

---

### 3. AI Analysis Module (analysis/)

**Purpose:** Static analysis and AI-powered error diagnosis

**Components:**
- **Static Analysis:**
  - `code_analyzer.py`: Python AST analysis
  - Syntax error detection
  - Undefined name detection
  - Ruff linter integration
  - Error context analysis

- **AI Integration:**
  - `ai_service.py`: Multi-provider AI integration
  - Provider routing (Gemini first, then OpenAI, then heuristic)
  - JSON response parsing with fallback
  - Error classification (authentication, quota, rate limits, etc.)

- **LogSense:**
  - `log_sense.py`: Log analysis
  - Sensitive data redaction
  - Error pattern detection
  - Log interpretation

**Data Flow:**
```
Code → Static Analysis → Syntax/Undefined Errors
      ↓
Execute → Error → Traceback → Error Parser
      ↓
Code + Error + Traceback → AI Provider → Diagnosis
      ↓
Display Diagnosis + Suggested Fixes
```

**Provider Fallback Strategy:**
1. Try Gemini (primary)
2. If fails, try OpenAI
3. If both fail, use heuristic (local) analysis
4. Always show static analysis results

---

### 4. Project Management Module (projects/, dashboard/)

**Purpose:** Project upload, file management, and project-level analysis

**Components:**
- **Upload Handling:**
  - `project_upload_service.py`: Secure file upload
  - Single file upload
  - Multiple file upload
  - ZIP archive upload with path traversal protection
  - File type validation
  - Size limits

- **Project Discovery:**
  - `project_discovery_service.py`: Project structure analysis
  - Language detection
  - Framework detection
  - File categorization
  - Import parsing
  - Cross-file dependency mapping

- **Project Analysis:**
  - `static_analysis_service.py`: Project-wide static analysis
  - `project_ai_service.py`: Project AI analysis
  - Issue tracking
  - Suggested fixes
  - Change history

- **Models:**
  - `Project`: Project metadata
  - `ProjectFile`: File content and path
  - `ProjectAnalysis`: Analysis results
  - `ProjectIssue`: Detected issues
  - `SuggestedFix`: AI-generated fixes
  - `AppliedChange`: Change tracking

**Data Flow:**
```
Upload → Validate → Extract → Store in Database
        ↓
    Discover Structure → Detect Languages/Frameworks
        ↓
    Static Analysis → Detect Issues
        ↓
    AI Analysis → Generate Explanations + Fixes
        ↓
    Display File Tree + Issues + Fixes
```

**Security:**
- ZIP path traversal protection
- File size limits
- File type validation
- Workspace isolation
- Temporary file cleanup

---

### 5. Code Repair and Verification Module (repair/, verification/)

**Purpose:** AI-powered repair generation and verification

**Components:**
- **Repair Generation:**
  - `repair_engine.py`: AI-powered repair
  - `local_repair_engine.py`: Heuristic repairs
  - Diff generation
  - Repair validation

- **Verification:**
  - `verification_engine.py`: Repair verification
  - Syntax checking
  - Execution testing
  - Output comparison

- **Models:**
  - `RepairAttempt`: Repair attempts tracking
  - `VerificationRun`: Verification results
  - `FileChange`: Change tracking
  - `AppliedChange`: Applied changes

**Data Flow:**
```
Error + Code → Repair Engine → AI Provider → Suggested Repair
      ↓
    Generate Diff → Display Original vs Proposed
      ↓
    User Approves → Apply Repair → Execute Verification
      ↓
    Syntax Check + Execution Test → Verification Result
      ↓
    Success → Update File | Failure → Rollback
```

**Repair Workflow:**
1. User clicks "Repair" or "Quick Fix"
2. System generates repair (AI or heuristic)
3. System displays diff (original vs proposed)
4. User reviews and approves/rejects
5. If approved, repair is applied
6. Verification runs automatically
7. User can rollback if needed

---

### 6. Learning Centre Module (learning/)

**Purpose:** Interactive debugging lessons and learning resources

**Components:**
- **Curriculum:**
  - Structured debugging topics
  - Error pattern lessons
  - Real-world examples
  - Practice problems

- **Lessons:**
  - Interactive code examples
  - Step-by-step debugging
  - Explanations of common errors
  - Follow-up questions

- **Recommendations:**
  - AI-powered lesson recommendations
  - Based on user's recent errors
  - Personalized learning path

**Models:**
- `LearningTopic`: Learning topics/categories
- `Lesson`: Debugging lessons with examples

**Data Flow:**
```
User Error → Analysis → Match Error Type → Recommend Lessons
      ↓
    User Completes Lesson → Update Progress
      ↓
    Track Learning History → Future Recommendations
```

---

## Database Schema

### Core Tables

**User Authentication:**
- `auth_user` - Django user table
- `accounts_aiprovidersettings` - AI provider preferences

**Workspace:**
- `dashboard_debuggingsession` - Debugging sessions
- Session history

**Projects:**
- `dashboard_project` - Project metadata
- `dashboard_projectfile` - File content
- `dashboard_projectanalysis` - Analysis results
- `dashboard_projectissue` - Detected issues
- `dashboard_suggestedfix` - Suggested fixes
- `dashboard_appliedchange` - Applied changes

**Repair:**
- `repair_repairattempt` - Repair attempts
- `verification_verificationrun` - Verification results
- `repair_filechange` - Change tracking

**Learning:**
- `learning_learningtopic` - Learning topics
- `learning_lesson` - Lessons

## API Architecture

### REST API Design

**Base URL:** `/api/v1`

**Authentication:** JWT Bearer tokens

**Response Format:** JSON

**Error Handling:**
- 400 Bad Request - Invalid input
- 401 Unauthorized - Authentication required
- 403 Forbidden - Permission denied
- 404 Not Found - Resource not found
- 413 Payload Too Large - File too large
- 429 Too Many Requests - Rate limited
- 500 Internal Server Error - Server error

### API Endpoints by Module

**Accounts:**
- `POST /auth/register/` - Register
- `POST /auth/login/` - Login
- `POST /auth/token/refresh/` - Refresh token
- `GET /auth/me/` - Get profile
- `PATCH /auth/me/` - Update profile

**Workspace:**
- `POST /execution/` - Execute code
- `GET /history/` - List sessions
- `GET /history/{id}/` - Get session

**Analysis:**
- `GET /analysis/health/` - Health check
- `POST /analysis/` - Analyze code

**Projects:**
- `GET /projects/` - List projects
- `POST /projects/` - Create project
- `POST /projects/upload/` - Upload ZIP
- `POST /projects/upload/single/` - Upload file
- `GET /projects/{id}/files/` - List files
- `PUT /projects/{id}/files/` - Save file
- `POST /projects/{id}/analyze/` - Analyze project
- `GET /projects/{id}/issues/` - Get issues

**Repair:**
- `POST /repair/generate/` - Generate repair
- `POST /repair/apply/` - Apply repair
- `POST /repair/reject/` - Reject repair
- `POST /verification/` - Verify repair

**Learning:**
- `GET /learning/` - List lessons
- `GET /learning/{id}/` - Get lesson
- `POST /learning/recommendations/` - Get recommendations

## Security Architecture

### Authentication
- JWT-based stateless authentication
- Access token expiration (configurable)
- Refresh token rotation
- Secure token storage (localStorage with fallback)

### Code Execution Security
- Isolated Python subprocess
- Resource limits (timeout, memory, output)
- No file system access
- No network access
- Resource cleanup after execution

### File Upload Security
- ZIP path traversal protection
- File type validation
- File size limits
- Workspace isolation
- Temporary file cleanup
- Malformed archive detection

### API Security
- CORS configuration
- Rate limiting (configurable)
- Permission checks
- Input validation
- SQL injection prevention (ORM)
- XSS prevention (HTML escaping)

### Data Privacy
- API keys stored server-side
- Sensitive data redaction in logs
- No code sent to AI without consent
- User consent required for external AI

## Performance Considerations

### Caching
- Analysis results caching (in-memory)
- AI provider health check caching
- Static file caching
- Session data caching

### Resource Management
- Execution timeouts
- Memory limits
- Output size limits
- Workspace cleanup management command
- Temporary file cleanup

### Scalability
- Stateless API design
- Database connection pooling
- Async AI requests
- Horizontal scaling ready (with PostgreSQL)

## Deployment Architecture

### Development
- SQLite database
- Local Django server
- Local frontend dev server
- Local file storage

### Production
- PostgreSQL database
- Gunicorn/Waitress WSGI server
- Nginx reverse proxy
- Static file serving (CDN or Nginx)
- Media file storage (S3 or similar)
- Supervisor/systemd process management
- Scheduled workspace cleanup

### Docker
- Backend container (Django + Gunicorn)
- Frontend container (Nginx + static files)
- PostgreSQL container
- Docker Compose orchestration

## Monitoring and Logging

### Logging
- Django application logs
- API request logs
- Error logs
- AI provider interaction logs
- Execution logs

### Health Checks
- Database connectivity
- AI provider availability
- Execution service availability
- API endpoint health

### Error Tracking
- Structured error responses
- Error classification
- User-friendly error messages
- Provider-specific error handling

## Future Enhancements

### Planned Features
- Real-time collaboration
- More language support (JavaScript, Java, C++)
- Advanced project analysis
- Custom AI models
- Plugin system
- Team workspaces
- CI/CD integration

### Scalability Improvements
- Redis caching
- Celery for async tasks
- Message queue for AI requests
- Microservices architecture
- Load balancing
