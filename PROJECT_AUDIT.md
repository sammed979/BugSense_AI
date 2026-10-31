# BugSense AI project audit

Audit date: 2026-11-01
Scope: current workspace source, Django route resolution and SQLite lesson catalogue, frontend entry points, package scripts, and test configuration.

## Findings and fixes

- **Learning route source is present.** `config/urls.py` mounts `apps.learning.urls` at `/api/v1/learning/`; the app registers the catalogue, dashboard, recommendations, lesson detail, exercise, quiz, and activity views. Django resolves `/api/v1/learning/dashboard/` to `learning_dashboard` and `/api/v1/learning/lessons/11/` to `learning_lesson`.
- **The screenshot’s ID 11 is valid in the current SQLite database.** It is the NameError lesson. The current catalogue contains 36 lessons.
- **Legacy Learning data is preserved.** Before release review, an untracked seed migration was found to delete existing `LearningTopic` rows (which could cascade into lesson progress). It now inserts missing curated titles with `get_or_create`; the Learning API, dashboard metrics, and recommendations only expose populated debugging lesson categories. Legacy rows and their progress stay in SQLite but are excluded from the error-focused UI.
- **Ignore rules now distinguish source from generated assets.** The old broad `static/` pattern hid `backend/static/`, which contains template assets; it now ignores generated `staticfiles/` output and allows source assets to be versioned. `.env`, SQLite databases, virtual environments, caches, and Node dependencies remain ignored.
- **Backend availability is the immediate local startup issue.** At audit time there was no process listening on port 8000. The screenshot’s dashboard 404 therefore came from a different/stale server state than the source currently in this workspace. Restart the backend from this project’s `backend` directory (instructions below) and refresh the frontend.
- **The frontend previously described every Learning 404 as a missing API endpoint.** Lesson detail 404s now get an item-specific message. Dashboard/catalogue 404s continue to indicate a backend route/version problem.
- **Repeated requests for one lesson could overlap.** The frontend API client now shares the in-flight detail request for the same lesson ID. A regression test covers this.
- **Application scrolling was page-level because the app shell had only minimum heights.** The root shell now fills the dynamic viewport and clips overflow at the shell; the active `.content-area` remains the vertical scroll container. Sidebar scrolling remains available when its contents exceed the viewport.
- **Learning remains authenticated.** Views use `IsAuthenticated`; the API client sends the stored Bearer access token and performs one refresh attempt before clearing an expired session. Authentication is not disabled to silence 401s.
- **Clipboard permission and cancellation outcomes are caught by `clipboardService` and shown as status messages by LogSense.** The “ERR Canceled” stack visible in the supplied screenshot references browser DevTools’ `clipboardService.ts`/`log.ts`, not this project’s `frontend/js/clipboard.js`; the project service does not log or rethrow an ordinary `AbortError`.

## Run locally

From the repository root, use two terminals:

```powershell
cd backend
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

```powershell
cd frontend
npm run dev
```

The frontend development server serves the static client at `http://127.0.0.1:5173`; the Django API is `http://127.0.0.1:8000/api/v1`. Sign in before opening Learning Centre because the catalogue, dashboard, activities, and lesson detail endpoints are user-authenticated. A missing/expired refresh session should return the user to login.

## File classification

| Classification | Findings |
| --- | --- |
| **KEEP** | Django settings, app URLs/views/serializers/models/migrations, API client, `app.js`, `index.html`, CSS, auth and clipboard modules, Monaco/workspace integrations, provider and LogSense services, database and user files. These are runtime paths or protected state. |
| **CLEAN** | Learning lesson request deduplication and route-vs-resource 404 messaging were cleaned up in the shared API client; shell overflow constraints were added to the existing stylesheet. |
| **MERGE** | No safe consolidation was established during this audit. The two Django `views_template*.py` files and archived-looking templates need route/import/deployment history review before any merge. |
| **DELETE** | None. No file was proven unused across static references, dynamic Django loading, scripts, and user data, so nothing was removed. |
| **REVIEW** | Legacy-looking `backend/apps/analysis/views_template.py`, `backend/apps/accounts/views_template2.py`, unused-looking standalone templates under `backend/templates/`, root-level workflow test scripts, `REPAIR_WORKFLOW_FIX_REPORT.md`, and generated/developer assets. Check external deployment and manual workflows before removal. |

The working tree already contained many modifications before this audit. A Git stash/checkpoint could not be created because the sandbox exposes `.git/index` as read-only (`git stash` returned `could not write index`). A recoverable ZIP source snapshot was created in the sandbox temporary directory before the release step; it contains source files only and excludes `.env`, SQLite databases, virtual environments, uploads, and caches. No existing project file, user-data database, or uncertain file was deleted.

## Test status

- `frontend`: `npm test` — **16 passed**.
- `backend`: `manage.py test apps.learning.tests --verbosity 1` — **10 passed**, including retained legacy topic/progress data.
- `backend`: `manage.py check` — **no issues**.
- `backend`: `manage.py makemigrations --check --dry-run` — **no model changes missing from migrations**.
- `git diff --check` — **passed** (Git emitted expected LF-to-CRLF working-copy notices).
- The full backend suite discovers 60 tests but does **not** pass in this environment. The execution workflow test fails when Python cannot open a temporary script under the sandbox-managed Windows temp directory (`Permission denied`; runner returns `-1`). The full run then stalled during provider integration tests and had to be stopped, so no complete-suite pass is claimed.
- A source scan found no credential-like literals in source/docs, and Git history contains no tracked `.env` or SQLite database paths. The local private `.env` and database are ignored and were excluded from the source backup.

The frontend project currently defines `dev`, `start`, and `test` scripts; it has no production build script. Browser-level visual verification was not available in this run.
