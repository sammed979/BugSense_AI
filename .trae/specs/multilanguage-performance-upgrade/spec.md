# BugSense AI — Multi-Language & Performance Upgrade

## Overview
- **Summary**: Upgrade BugSense AI from a Python-only debugging studio into a fast, multi-language (Python, Java, C, C++, JavaScript) AI debugging and learning platform, and fix the slow-loading / blank-page experience.
- **Purpose**: Let students paste or upload code in any supported language without manual selection; the platform auto-detects the language, detects and explains errors, generates corrected code in the same language, and lets students verify the fix. The frontend must render immediately and never blank-screen while the backend warms up or an API call is in flight.
- **Target Users**: Students and beginner developers learning to debug programs.

## Goals
- Eliminate blank-screen / slow-load by rendering the layout shell before any API call and showing loading states instead of empty screens.
- Add automatic, confidence-based programming language detection for Python, Java, C, C++, and JavaScript (extensible to more).
- Implement language-specific analysis, same-language repair, and sandboxed execution/verification for each supported language.
- Extend the educational explanation engine and LogSense to all supported languages while keeping the deterministic-first, AI-supplemental contract.
- Keep OpenAI as the primary AI provider and Gemini as the secondary provider; AI must explain and improve detected results, never replace reliable compiler/interpreter output.
- Preserve all existing features: auth, dashboard, workspace, Python analysis/repair/execution, ZIP upload, comparison, rollback, LogSense, history, Learning Centre, OpenAI/Gemini, PostgreSQL, Vercel + Render deployment.

## Non-Goals
- Adding a build step or framework (React/Vue) to the frontend. The vanilla SPA architecture is preserved.
- True container-level / VM-level sandboxing. Render free tier does not support nested containers; execution uses OS-level resource limits (CPU time, memory, file size, process count) plus temp directories and network restriction where the OS allows it. This is a best-effort sandbox for student code, not a hostile-attacker boundary.
- Supporting languages beyond the five listed (Python, Java, C, C++, JavaScript) in this upgrade, though the architecture must be extensible.
- Real-time collaborative editing or live pair-programming.
- Mobile native apps.

## Background & Context
- The frontend boots on `window.addEventListener('load', handleRoute)`, which waits for every resource (images, fonts, stylesheets, Monaco CDN) before rendering. On a cold load or slow network this produces a blank dark screen. Monaco itself is loaded from a CDN with no visible loading placeholder.
- All four backend endpoints (`/analysis/analyze/`, `/execution/execute/`, `/repair/`, `/verification/`) reject any `language` other than `python` with HTTP 400.
- `backend/sandbox/python_runner.py` runs user code in a subprocess with a timeout but sets **no** `resource.setrlimit` limits (CPU, memory, file size, process count) and does not restrict network access. For C/C++ this is unsafe.
- The deterministic-first diagnosis pipeline (ErrorParser → CodeAnalyzer.analyze_error_context → explain_local) and the `educational_diagnosis` / `ai_supplement` separation are already in place for Python and must be generalized.
- Deployment: frontend on Vercel (root + `/frontend` mirror), backend on Render (Procfile → gunicorn). Neon PostgreSQL free tier. Render native runtime does not include gcc/g++/jdk/node by default; they must be installed via the Render build command.

## Functional Requirements

### Performance & Reliability
- **FR-1 (Immediate render)**: The application shell (sidebar + current route container) is rendered synchronously on DOMContentLoaded, before any network request.
- **FR-2 (Loading indicators)**: Every async section (dashboard stats, workspace editor, AI provider status, LogSense result, history, learning content) shows a non-blank loading indicator while its data is being fetched.
- **FR-3 (Graceful API failure)**: A failed API request shows a meaningful error message and preserves the current page state; it never throws an uncaught exception that blanks the app.
- **FR-4 (No infinite loading)**: Every API request has a timeout and a terminal failure state. A slow or hanging request cannot leave a spinner forever.
- **FR-5 (Render cold-start handling)**: The frontend detects a cold/unreachable backend (connection refused / timeout on the first request), shows a "Warming up backend…" message, and retries with exponential backoff (e.g. 1s, 2s, 4s, 8s) up to a cap. Only one retry loop runs at a time.
- **FR-6 (No full-reload on retry)**: Retries do not call `window.location.reload()`; they re-issue the failed API call and update the relevant UI section.
- **FR-7 (Independent section rendering)**: Dashboard, Workspace, LogSense, History, and Learning Centre render independently; a failure in one does not block the others.

### Automatic Language Detection
- **FR-8 (Detection inputs)**: Detection uses file extension (when a file is uploaded), source-code keywords, syntax patterns, import/header statements, function/class declarations, data types, and available source-code parsing (AST for Python, `node --check` for JS, extension + heuristics for Java/C/C++).
- **FR-9 (Confidence-based)**: Detection returns a language label and a confidence score (0–1). If confidence is below a threshold, the system states the language could not be identified confidently and asks for clarification instead of guessing.
- **FR-10 (Display detected language)**: The detected language is shown to the user in the workspace.
- **FR-11 (Edge cases)**: Detection handles incorrect file extensions, missing extensions, pasted code, incomplete code, and multiple languages inside one ZIP.
- **FR-12 (Supported set)**: Languages supported: Python, Java, C, C++, JavaScript.

### Language-Specific Analysis
- **FR-13 (Per-language handlers)**: A reusable architecture with a separate analysis handler per language; the endpoint dispatches based on the detected language.
- **FR-14 (Python errors)**: SyntaxError, IndentationError, NameError, TypeError, KeyError, IndexError, ValueError, ImportError, ZeroDivisionError, AttributeError.
- **FR-15 (Java errors)**: Compilation errors, syntax errors, type errors, NullPointerException, ArrayIndexOutOfBoundsException, ArithmeticException, NumberFormatException, ClassNotFoundException.
- **FR-16 (C errors)**: Compilation errors, syntax errors, undeclared variables, missing headers, type errors, pointer errors, segmentation faults, memory errors.
- **FR-17 (C++ errors)**: Compilation errors, syntax errors, type errors, undefined references, segmentation faults, invalid memory access, runtime exceptions.
- **FR-18 (JavaScript errors)**: SyntaxError, ReferenceError, TypeError, RangeError, Promise/async errors, undefined property access.
- **FR-19 (Error taxonomy)**: Clearly distinguish syntax, compilation, runtime, logical errors, and warnings.

### Same-Language Error Correction
- **FR-20 (Language preservation)**: Corrected output is always in the same language as the input. The AI prompt enforces this and the response is validated to be in the detected language.
- **FR-21 (Minimal correction)**: The repair preserves intended functionality, existing functions/classes/structure, and makes the smallest appropriate change; it does not rewrite the whole program.
- **FR-22 (Side-by-side + rollback)**: Original and corrected code are shown side by side with changed lines highlighted; the user can review, accept, or roll back.

### Educational Explanation Engine
- **FR-23 (10-point explanation)**: For every detected error, provide: Error Name, Programming Language, Error Location (file/function/line), What Happened, Why It Happened, Step-by-Step explanation, How to Fix, Corrected Code, Why the Fix Works, How to Prevent.
- **FR-24 (Beginner-friendly)**: Technical terms are explained in simple English with small examples where useful.
- **FR-25 (Confirmed vs possible)**: Confirmed facts (from compiler/interpreter output and source) are separated from possible causes. AI never invents root causes.

### Sandboxed Execution & Verification
- **FR-26 (Per-language runners)**: Python → interpreter; Java → javac + java; C → gcc; C++ → g++; JavaScript → node.
- **FR-27 (Isolation & limits)**: Each run uses a unique temp directory, a wall-clock timeout, and OS resource limits (CPU time, max memory, max file size, max process count) applied via `resource.setrlimit` on Linux. Network access is restricted where the OS permits (e.g. `unshare --net` when available; otherwise documented as not isolated).
- **FR-28 (Output capture & cleanup)**: stdout, stderr, exit code, and duration are captured. Temp files are always deleted. Output is truncated to a configurable byte limit.
- **FR-29 (No in-process execution)**: User code never runs inside the Django worker process.
- **FR-30 (Verification)**: A repair is verified by compiling/running the corrected code in the sandbox; the platform does not claim a repair works unless verification passes (where execution is supported).

### Multi-Language LogSense
- **FR-31 (Log language detection)**: LogSense identifies the log type and source language (Python traceback, Java exception, C/C++ compiler/runtime error, JavaScript error, Django/server log, database/API error).
- **FR-32 (Log fields)**: For each log, extract error type, message, file, and line number; explain entries; group related entries into one incident; provide root cause, impact, troubleshooting steps, and possible corrections.
- **FR-33 (No over-classification)**: LogSense does not classify every log as Python and does not show generic explanations when the actual error is identifiable.

### AI Integration
- **FR-34 (Provider order)**: OpenAI primary, Gemini secondary, with fallback.
- **FR-35 (Deterministic-first)**: AI receives the deterministic diagnosis as context and is instructed to explain/expand on it, not replace it. AI output is kept separate from confirmed facts.
- **FR-36 (Anti-hallucination)**: AI must not invent filenames, line numbers, or exceptions; it must use the actual submitted source code and logs.

### Preservation
- **FR-37 (Existing features preserved)**: All existing features listed in Goals continue to work with their existing API contracts (field names are preserved; new fields are additive).

## Non-Functional Requirements
- **NFR-1 (First paint)**: The app shell is visible within the time to parse `app.js` (no waiting for images/fonts/CDN).
- **NFR-2 (API timeout)**: All API requests have a client-side timeout (analysis ≤ 60s, execution ≤ 30s, others ≤ 15s) with a clear timeout message.
- **NFR-3 (Backend non-blocking)**: Slow AI operations do not block the health endpoint or unrelated endpoints.
- **NFR-4 (Security)**: Execution sandbox applies OS resource limits; user code runs in a subprocess with a clean environment and no access to the project directory.
- **NFR-5 (Backward compatibility)**: Existing API response fields (`ai_analysis`, `static_analysis`, `runtime_diagnosis`, `traceback_analysis`, `educational_diagnosis`, `session_id`, `analysis_status`; LogSense fields) are preserved; new fields are additive.
- **NFR-6 (Testability)**: Every supported language has automated tests covering valid programs, syntax errors, compilation errors, runtime errors, multiple errors, incomplete code, and incorrect file extensions.
- **NFR-7 (No hardcoded samples)**: No hardcoded sample explanations in production code.

## Constraints
- **Technical**: Vanilla JS frontend (no build framework); Django 5 + DRF backend; Neon PostgreSQL free tier; Render free tier for backend; Vercel for frontend. OpenAI SDK pinned ≥ 1.55.3.
- **Business**: Cost constraint — use Neon free tier, Render free tier. Execution toolchains (gcc, g++, jdk, node) must be installable on Render via the build command without paid add-ons.
- **Dependencies**: Existing OpenAI + Gemini integration must remain primary/secondary. `EXECUTION_ENABLED` gates execution.
- **Sandboxing limit**: Render free tier does not support nested containers or seccomp profiles; sandboxing is best-effort via `resource.setrlimit` + temp dirs + subprocess isolation.

## Assumptions
- Render's build environment allows installing `build-essential`, `default-jdk`, and `nodejs` via apt in the build command (or the Dockerfile path is used). If a toolchain is unavailable at runtime, execution for that language reports "unavailable" rather than crashing.
- The existing `educational_diagnosis` / `ai_supplement` contract from the previous Python work is the template for all languages.
- The frontend's `js/app.js` and `frontend/js/app.js` must remain byte-identical (mirror deployment requirement).

## Open Questions
- [ ] **Render toolchain install path**: Should execution toolchains be installed via Render's `buildCommand` (apt-get) or by switching the backend to deploy from `docker/Dockerfile.backend`? (Default plan: update `Procfile`/build command to install toolchains; document both options.)
- [ ] **JavaScript execution on Render**: Render's Python native runtime does not include Node.js. Is installing Node.js in the build command acceptable, or should JS execution use a serverless function? (Default plan: install nodejs in the build command.)

## Acceptance Criteria

### AC-1: App shell renders before any API call
- **Type**: `rule`
- **Given**: A user opens the app with a cold cache and the backend is unreachable
- **When**: The browser finishes parsing `app.js`
- **Then**: The sidebar and the current route's container are visible; no blank dark screen appears regardless of network state
- **Pass Condition**: Boot is triggered on `DOMContentLoaded` (not `window.load`), and `handleRoute` paints the shell synchronously
- **Evidence**: Code inspection of `app.js` boot line; manual load with backend offline

### AC-2: Failed API call never blanks the app
- **Type**: `rule`
- **Given**: Any API endpoint returns an error or times out
- **When**: The frontend receives the error
- **Then**: A meaningful error message is shown in the relevant section; the rest of the app remains interactive; no uncaught exception reaches `window.onerror` as a blank page
- **Pass Condition**: All `await api.*` calls are wrapped in try/catch with UI feedback
- **Evidence**: Code inspection + manual test by stopping the backend

### AC-3: Render cold-start retries with backoff
- **Type**: `rule`
- **Given**: The backend returns connection-refused or times out on the first request
- **When**: The frontend makes the request
- **Then**: A "Warming up backend…" indicator appears; the request is retried with exponential backoff (1s, 2s, 4s, 8s, then stop) without reloading the page; only one retry loop runs
- **Pass Condition**: A single retry manager with backoff exists and is used by API calls
- **Evidence**: Code inspection of the retry manager

### AC-4: Automatic language detection for 5 languages
- **Type**: `rule`
- **Given**: Source code in Python, Java, C, C++, or JavaScript (pasted or uploaded)
- **When**: Detection runs
- **Then**: The correct language is returned with confidence ≥ 0.7 for representative samples of each language
- **Pass Condition**: A test suite with ≥ 2 samples per language returns the correct label and confidence ≥ 0.7
- **Evidence**: `tests/test_language_detection.py` passing

### AC-5: Low-confidence detection asks for clarification
- **Type**: `rule`
- **Given**: Ambiguous or incomplete source code
- **When**: Detection confidence is below the threshold
- **Then**: The response indicates the language could not be identified confidently and does not guess
- **Pass Condition**: A test with a short ambiguous snippet returns `confident: false` and no guessed language
- **Evidence**: Test asserting `confident is False` for ambiguous input

### AC-6: Each language's analysis detects its listed errors
- **Type**: `rubric`
- **Dimension**: Breadth and accuracy of language-specific error detection
- **Scale**: 1-5
- **Anchors**: 1 = only Python works; 3 = Python + 2 others detect their named errors; 5 = all 5 languages detect every error listed in FR-14..FR-18 with correct type/message/location
- **Pass Threshold**: >= 4
- **Evidence**: `tests/test_multilanguage_analysis.py` results

### AC-7: Repaired code is in the same language as input
- **Type**: `rule`
- **Given**: A buggy program in language L
- **When**: Repair is requested
- **Then**: The returned `repaired_code` is syntactically valid code in language L (validated by the language's parser/compiler), not translated to another language
- **Pass Condition**: For each language, a repaired sample compiles/lints cleanly in that language
- **Evidence**: `tests/test_multilanguage_repair.py` + verification step

### AC-8: Sandboxed execution applies resource limits
- **Type**: `rule`
- **Given**: A program that exceeds CPU time or memory
- **When**: It is executed in the sandbox
- **Then**: The process is killed within the timeout; the runner returns a timed-out / killed status; no Django worker is blocked
- **Pass Condition**: An infinite-loop program is terminated within the configured timeout; a memory-bomb is killed
- **Evidence**: `tests/test_sandbox_limits.py` passing

### AC-9: User code never runs in the Django process
- **Type**: `rule`
- **Given**: Any supported language execution request
- **When**: The runner executes the code
- **Then**: Execution happens in a subprocess (subprocess.Popen) with a clean environment and a temp working directory, not via `exec`/`eval` in the Django worker
- **Pass Condition**: Code inspection of every runner shows `subprocess.Popen` with isolated env/cwd
- **Evidence**: Code review of `backend/sandbox/*`

### AC-10: LogSense identifies non-Python logs
- **Type**: `rule`
- **Given**: A Java exception, a C compiler error, and a JavaScript ReferenceError log
- **When**: LogSense processes them
- **Then**: Each is classified with the correct source language and error type; not classified as Python; not "unknown"
- **Pass Condition**: Tests assert correct `technologies`/`error_type` for each sample
- **Evidence**: `tests/test_logsense.py` additions passing

### AC-11: Educational explanation has all 10 sections
- **Type**: `rule`
- **Given**: A detected error in any supported language
- **When**: The educational diagnosis is returned
- **Then**: It contains all 10 sections: error name, language, location, what happened, why, step-by-step, how to fix, corrected code, why fix works, prevention
- **Pass Condition**: Each section key is present and non-empty for a sample error
- **Evidence**: `tests/test_educational_diagnosis.py` (or existing tests) asserting all 10 keys

### AC-12: Existing features still work
- **Type**: `rule`
- **Given**: The existing test suite and existing API contracts
- **When**: The upgrade is applied
- **Then**: All pre-existing tests pass; existing API response field names are unchanged
- **Pass Condition**: `python manage.py test` (excluding the known environment-dependent Render settings tests) passes with no regressions
- **Evidence**: Full test run output

### AC-13: Frontend mirror copies stay identical
- **Type**: `rule`
- **Given**: A change to `js/app.js` or `frontend/js/app.js`
- **When**: The change is committed
- **Then**: Both files have identical SHA-256 hashes
- **Pass Condition**: `Get-FileHash` of both files returns the same hash
- **Evidence**: Hash comparison in the final report

### AC-14: Backend health and unrelated endpoints remain fast
- **Type**: `rubric`
- **Dimension**: Backend responsiveness under AI load
- **Scale**: 1-5
- **Anchors**: 1 = /health/ hangs while an AI analyze runs; 3 = /health/ responds but slowly; 5 = /health/ and dashboard endpoints respond in < 500ms even while a long AI analyze is in flight
- **Pass Threshold**: >= 4
- **Evidence**: Manual timing of /health/ during an analyze call
