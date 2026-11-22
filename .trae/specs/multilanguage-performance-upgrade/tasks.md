# BugSense AI — Multi-Language & Performance Upgrade: Implementation Plan

## Task 1: Fix frontend blank-screen by booting on DOMContentLoaded and adding loading states
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Change the app boot from `window.addEventListener('load', handleRoute)` to `DOMContentLoaded` (or call `handleRoute()` at script end) so the shell paints before images/fonts/Monaco CDN.
  - Add a visible loading placeholder inside the Monaco container while it loads (so the workspace is never blank during CDN load).
  - Wrap every top-level `await window.api.*` call site in try/catch with a meaningful inline error message; never let an uncaught rejection blank the page.
  - Add a global `window.onerror` / `unhandledrejection` handler that shows a fallback message instead of a blank screen.
  - Apply changes to both `js/app.js` and `frontend/js/app.js` (keep identical).
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-13
- **Test Requirements**:
  - `rule` TR-1.1: Boot is triggered on `DOMContentLoaded` (not `window.load`); evidence: grep `app.js` boot line.
  - `rule` TR-1.2: Every `js/app.js` and `frontend/js/app.js` have identical SHA-256 hashes after edits; evidence: `Get-FileHash` output.
  - `rule` TR-1.3: With the backend stopped, opening `#/workspace` renders the sidebar and editor shell without a blank screen; evidence: manual browser test.

## Task 2: Add Render cold-start retry manager with exponential backoff
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Add a `RetryManager` (or equivalent) in `js/api.js` that, on connection-refused / timeout, shows a "Warming up backend…" message and retries with exponential backoff (1s, 2s, 4s, 8s, then stop) without `window.location.reload()`.
  - Ensure only one retry loop runs at a time (shared inflight promise).
  - Integrate into `APIClient.request` so the first failing call triggers warm-up and subsequent calls share the warm-up promise.
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `rule` TR-2.1: A simulated connection-refused triggers at most 4 retries with 1/2/4/8s spacing and then stops; evidence: unit test or manual network tab.
  - `rule` TR-2.2: Retries never call `window.location.reload`; evidence: grep for `location.reload` returns nothing in the retry path.

## Task 3: Implement automatic language detection service
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Create `backend/services/language_detector.py` with a `LanguageDetector` class.
  - Signatures: `detect(source_code, filename=None) -> {language, confidence, confident, evidence}.
  - Use file extension first, then keyword/heuristic scoring (imports, keywords, data types, comment styles) to disambiguate (e.g. `#include` → C/C++; `public class` → Java; `def ` → Python; `function`/`const`/`let` → JS).
  - Use `ast.parse` to confirm Python; `node --check` to confirm JS (when node available).
  - Return `confident=False` when the top two scores are close or no signal.
  - Support Python, Java, C, C++, JavaScript; extensible registry.
- **Acceptance Criteria Addressed**: AC-4, AC-5
- **Test Requirements**:
  - `rule` TR-3.1: `tests/test_language_detection.py` passes with ≥2 samples per language returning correct label and confidence ≥ 0.7; evidence: test output.
  - `rule` TR-3.2: A short ambiguous snippet returns `confident=False`; evidence: test assertion.

## Task 4: Build multi-language sandbox runners with resource limits
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Refactor `backend/sandbox/python_runner.py` into a base `SandboxRunner` base class plus `PythonRunner`, `JavaRunner`, `CRunner`, `CppRunner`, `JavaScriptRunner` (a`backend/sandbox/`package.
  - Each runner: write source to a temp dir, run in subprocess with a wrapper that applies `resource.setrlimit` (CPU, AS/memory, file size, nproc), clean env, stdin=DEVNULL, timeout, capture stdout/stderr/exit_code/duration, clean temp dir.
  - Network restriction: attempt `unshare --net` when available (Linux); document fallback.
  - Add a `runner_registry` mapping language → runner class and a `get_runner(language)` factory.
  - Update Procfile/build docs to install `build-essential`, `default-jdk`, `nodejs`.
- **Acceptance Criteria Addressed**: AC-8, AC-9
- **Test Requirements**:
  - `rule` TR-4.1: An infinite-loop Python/C program is killed within the timeout; evidence: `tests/test_sandbox_limits.py`.
  - `rule` TR-4.2: Every runner uses `subprocess.Popen` with isolated `cwd`=temp dir and a clean `env`; evidence: code review.
  - `rule` TR-4.3: Java/C/C++/JS runners produce correct exit code / stdout for a trivial program; evidence: tests where toolchain present.

## Task 5: Generalize CodeAnalyzer to multi-language analysis handlers
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 3, Task 4
- **Description**:
  - Create per-language analysis handlers in `backend/services/languages/` (e.g. `python_analyzer.py`, `java_analyzer.py`, `c_analyzer.py`, `cpp_analyzer.py`, `js_analyzer.py`) behind a common interface `analyze(code, error_message, runtime_output) -> diagnosis dict.
  - Python: keep existing AST/symtable/ruff + ErrorParser.
  - Java: parse javac compilation error lines (`*.java:line: error: message`); runtime exception lines (`Exception in thread ...`).
  - C/C++: parse gcc/g++ error lines (`file:line:col: error:`); runtime segfault (`Segmentation fault`).
  - JS: `node --check` syntax; runtime ReferenceError/TypeError lines.
  - Each handler returns the 10-section educational diagnosis keys and the existing legacy keys (`error_category`, `summary`, `possible_causes`, `confidence`, `detection_source='deterministic'`).
  - Add a registry `get_analyzer(language)`.
- **Acceptance Criteria Addressed**: AC-6, AC-11
- **Test Requirements**:
  - `rule TR-5.1: `tests/test_multilanguage_analysis.py` covers each named error type per language; evidence: passing tests.
  - `rule` TR-5.2: Each analysis result contains all 10 educational keys; evidence: test asserting keys.

## Task 6: Wire multi-language analysis endpoint (analyze/execute/repair/verify)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 3, Task 4, Task 5
- **Description**:
  - Update `/analysis/analyze/`: accept `language` or auto-detect from source; dispatch to the language analyzer; keep existing response fields.
  - `/execution/execute/`: dispatch to the runner for the detected/passed language.
  - `/repair/`: pass detected language to provider_router so AI prompt enforces same-language repair; validate repaired code compiles/lints in that language before returning.
  - `/verification/`: run the repaired code through the language runner.
  - Keep Python behavior for Python.
- **Acceptance Criteria Addressed**: AC-6, AC-7, AC-12
- **Test Requirements**:
  - `rule` TR-6.1: Each endpoint accepts a Java/C/C++/JS sample and returns a 200 with the correct language field; evidence: `apps.analysis.tests` additions.
  - `rule` TR-6.2: A repaired Java sample compiles with javac; evidence: `tests/test_multilanguage_repair.py`.

## Task 7: Multi-language repair prompt + same-language validation
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 5, Task 6
- **Description**:
  - Update `provider_router.py` and `ai_service.py` prompts to require same-language correction, minimal diff, and anti-hallucination rules for each language.
  - Add a post-validation step: run the language's static check (ast.parse / javac / gcc / g++ / node --check) on `repaired_code`; if invalid, reject the repair (do not return invalid code).
- **Acceptance Criteria Addressed**: AC-7, AC-36
- **Test Requirements**:
  - `rule` TR-7.1: Repaired code for each language passes the language's compile/check; evidence: tests.

## Task 8: Extend LogSense to multi-language logs
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 3
- **Description**:
  - In `backend/services/log_sense.py`, add log-source detection (Java stack traces, gcc/g++ errors, JS errors, Django/API errors) alongside existing Python.
  - Classify log `technologies` and `error_type` per language.
  - Reuse the 10-section explanation for identifiable errors.
- **Acceptance Criteria Addressed**: AC-10, AC-33
- **Test Requirements**:
  - `rule` TR-8.1: Java exception, C compiler error, JS ReferenceError each classified correctly; evidence: `tests/test_logsense.py` additions.

## Task 9: Frontend workspace multi-language UI
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 3, Task 6
- **Description**:
  - Replace the manual language `<select>` with auto-detection: on paste/upload, call the detection (or client-side quick hint) and show detected language; allow override.
  - Pass `language` to analyze/execute/repair calls.
  - Render detected language badge and the 10 educational sections for all languages.
  - Keep both app.js and frontend/js/app.js identical.
- **Acceptance Criteria Addressed**: AC-10, AC-11
- **Test Requirements**:
  - `rule` TR-9.1: Pasting Java shows "Java" detected; evidence: manual.
  - `rule` TR-9.2: both app.js files identical hash; evidence: Get-FileHash.

## Task 10: Update deployment config for multi-language toolchains
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 4
- **Description**:
  - Update `Procfile` / Render build command to install build-essential, default-jdk, nodejs (or document Dockerfile path).
  - Update `Dockerfile.backend` to include gcc, g++, default-jdk, nodejs.
  - Document in DEPLOYMENT_GUIDE.md.
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `rule` TR-10.1: Dockerfile.backend installs gcc, g++, javac/java, node; evidence: Dockerfile review.

## Task 11: Full regression test run and final report
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1-10
- **Description**:
  - Run the full backend test suite (excluding known env-dependent Render settings tests).
  - Run `manage.py check`, `compileall`, `node --check` on both app.js.
  - Verify mirror hash check.
  - Produce the final report (root causes, modified files, supported languages, detection results, repair/execution results, performance before/after, limitations).
- **Acceptance Criteria Addressed**: AC-12, AC-13, AC-14
- **Test Requirements**:
  - `rule` TR-11.1: Full test suite passes (except known env tests); evidence: test output.
  - `rule` TR-11.2: `manage.py check` clean; `node --check` clean on both app.js; evidence: command output.
