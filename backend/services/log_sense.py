"""Evidence-led local interpretation for technical logs. Never executes log contents."""
import re

MAX_LOG_CHARS = 100_000
_REDACTIONS = [
    ('credential', re.compile(r'(?i)\b(api[_ -]?key|token|password|secret|authorization)\b\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+')),
    ('bearer_token', re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*')),
    ('aws_key', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('provider_token', re.compile(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|AIza[0-9A-Za-z_-]{30,})\b')),
    ('jwt', re.compile(r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b')),
]


def redact_secrets(value):
    output, kinds = value, []
    for kind, pattern in _REDACTIONS:
        if kind == 'credential':
            output, count = pattern.subn(lambda match: f'{match.group(1)}=[REDACTED]', output)
        else:
            output, count = pattern.subn('[REDACTED]', output)
        if count:
            kinds.append(kind)
    return output, kinds


RULES = [
    ('Django missing table', 'Python / Django / SQLite', r'(?:no such table:\s*["`]?([\w.]+)|relation\s+["\']([^"\']+)["\']\s+does not exist)', 'The connected database does not contain the referenced table `{identifier}`.', 'Confirmed: the database engine reported that table `{identifier}` is absent in the database connection used by this process. This log does not show a connectivity failure. The reason the table is absent is not established.', ['Check `DATABASES` in the active settings and confirm the expected database file or server/schema.', 'Run `python manage.py showmigrations` and check whether the relevant app migrations are applied.', 'If model changes have no migration, run `python manage.py makemigrations <app>` after reviewing the generated migration.', 'Apply pending migrations with `python manage.py migrate`.', 'If this table belongs to a custom user model, confirm `AUTH_USER_MODEL` and that its app migration is installed before dependent migrations.'], 'A table is created by schema migrations; the application can connect successfully while a required table is missing.', 'Apply reviewed migrations to the same configured database the application uses.'),
    ('Python NameError', 'Python', r'NameError:\s*name\s+[\'\"]([^\'\"]+)[\'\"]\s+is not defined', 'Python reached a reference to `{identifier}`, but no variable with that name was available in the current scope.', 'This confirms that `{identifier}` was unresolved at runtime. The log cannot tell whether it was misspelled, never assigned, or out of scope.', ['Check the spelling and capitalization of `{identifier}`.', 'Define or import `{identifier}` before the failing line, or replace it with the intended existing name.', 'If the name is local to a function, pass it in or define it in that function.'], 'Python resolves variable names in the active local and enclosing scopes before raising NameError.', 'Use linters and tests that execute the failing path.'),
    ('Python TypeError', 'Python', r'TypeError:\s*(?!Cannot read properties)(.+)', 'Python rejected an operation because its value or argument types do not fit that operation: {detail}', 'The TypeError message identifies the operation Python could not perform; inspect the values at that call site.', ['Read the full TypeError text to identify the operation and expected types.', 'Inspect the values immediately before the reported call.', 'Convert or validate the value only if that matches the intended data model.'], 'Dynamic typing permits values of different types, but each operation still has type requirements.', 'Validate inputs at system boundaries and test both normal and edge values.'),
    ('Python IndexError', 'Python', r'IndexError:\s*(.+)', 'Python tried to access a sequence position that is not present: {detail}', 'The log establishes an invalid index access; it does not establish why the sequence was shorter than expected.', ['Inspect the sequence length at the failing line.', 'Check loop bounds and whether an empty sequence is possible.', 'Guard the access or iterate over the sequence directly.'], 'Python sequence indexes start at zero, and the last valid index is length minus one.', 'Test empty, one-item, and boundary-sized sequences.'),
    ('Python ModuleNotFoundError', 'Python', r"ModuleNotFoundError:\s*No module named\s+[\'\"]?([^\'\"\s]+)", 'Python could not import the module `{identifier}` in the environment running this process.', 'The active interpreter could not resolve `{identifier}`. This can mean the dependency is absent, the import name is wrong, or a different Python environment is active.', ['Confirm the import spelling and the package that provides `{identifier}`.', 'Run `python -m pip show {identifier}` using the same interpreter that starts the app.', 'Install the verified package in that environment or activate the intended virtual environment.'], 'Python imports modules from the active interpreter environment; installing into another environment does not make them available here.', 'Use a virtual environment and record dependencies in a requirements file.'),
    ('Python ZeroDivisionError', 'Python', r'ZeroDivisionError:\s*(.+)', 'Python attempted to divide by zero: {detail}', 'The exception confirms the divisor evaluated to zero at runtime.', ['Inspect the denominator at the reported operation.', 'Decide how zero should be handled for this calculation.', 'Add a zero check or use a domain-appropriate alternative before dividing.'], 'Division by zero is undefined for ordinary real-number arithmetic and raises an exception in Python.', 'Test zero and boundary values for every division operation.'),
    ('Python SyntaxError', 'Python', r'SyntaxError:\s*(.*)', 'Python could not parse the source text: {detail}', 'The parser rejected the source before that code could run. The reported line and caret are the strongest location evidence.', ['Inspect the reported line and the line immediately before it.', 'Balance quotes, parentheses, brackets and indentation.', 'Run the file again after correcting the syntax at the reported location.'], 'A parser checks source grammar before executing the program.', 'Run a syntax check or formatter in the edit loop.'),
    ('Django migration error', 'Django', r'(?:No migrations? detected|no such column|OperationalError:.*(?:table|column|locked)|InconsistentMigrationHistory|Migration\w*Conflict)', 'Django’s migration state and the database schema appear inconsistent: {detail}', 'This message points to migration discovery, ordering, or schema state. It does not by itself prove which migration should be applied or reversed.', ['Read the complete migration error and identify the app or table it names.', 'Check `python manage.py showmigrations` and inspect recent migration files.', 'Create or apply a migration only after confirming the model and database state.'], 'Django migrations are versioned schema changes; model code and applied database migrations can drift apart.', 'Review generated migrations and back up important databases before schema changes.'),
    ('Django 404', 'Django', r'(?:Page not found \(404\)|Not Found:)', 'Django could not match the requested path to a resource: {detail}', 'The response confirms that the requested URL was not found in this environment. The log alone does not identify whether the cause is a missing route, wrong prefix, or wrong server.', ['Compare the requested path with Django’s `urlpatterns`, including prefixes and trailing slashes.', 'Confirm the browser is reaching the intended Django process and project settings.', 'Check route authentication or resource existence separately; a 404 does not prove a view crashed.'], 'Django resolves request paths against the active URL configuration in order.', 'Test URL names with Django’s resolver and keep one source of truth for API prefixes.'),
    ('Java NullPointerException', 'Java', r'NullPointerException(?::\s*(.*))?', 'Java attempted to use a reference whose value was null: {detail}', 'The exception confirms a null dereference. A nearby stack frame can identify the method and source line, but the log may not reveal which assignment produced null.', ['Use the first application stack frame to find the dereference.', 'Trace where that reference is assigned and whether the value can be absent.', 'Validate or initialize the value before calling methods on it.'], 'Java object references can be null; dereferencing one throws NullPointerException.', 'Use nullability annotations and validate optional values at boundaries.'),
    ('Java compilation error', 'Java', r'(?:\.java:\d+:\s*error:|error:\s+.*(?:expected|cannot find symbol|incompatible types))', 'The Java compiler rejected source code: {detail}', 'Compilation stopped before the affected code could execute. Use the compiler’s source file and line when present.', ['Read the first compiler error; later messages may be follow-on errors.', 'Inspect the named Java file and line, plus nearby declarations and imports.', 'Recompile after fixing the first confirmed diagnostic.'], 'The Java compiler performs syntax and type checks before producing runnable bytecode.', 'Compile in continuous integration with the same JDK version used for development.'),
    ('JavaScript ReferenceError', 'JavaScript / Node.js', r'ReferenceError:\s*(.+)', 'JavaScript tried to use a name that is not defined in the current scope: {detail}', 'The runtime could not resolve the referenced identifier. The stack frame, if present, locates where it was evaluated.', ['Check the identifier spelling and capitalization.', 'Confirm the variable is declared, imported, and in scope before this statement runs.', 'Check whether the code path runs before module initialization.'], 'JavaScript resolves identifiers lexically; an undeclared identifier raises ReferenceError.', 'Enable lint rules for undefined names and add tests for the failing path.'),
    ('JavaScript TypeError', 'JavaScript / Node.js', r'TypeError:\s*(.+)|Cannot read properties of (?:undefined|null) \(reading [\'\"]?([^\'\")]+)', 'JavaScript could not complete an operation on the value shown: {detail}', 'The message identifies an operation applied to an invalid or unexpected value; inspect that value at the reported stack frame.', ['Inspect the object and property named in the message.', 'Trace where the value is created and whether it can be null, undefined, or another type.', 'Validate the value or handle the absent case before using it.'], 'JavaScript operations can fail at runtime when a value does not have the expected shape.', 'Validate API responses and represent loading or missing data explicitly.'),
    ('React rendering error', 'React', r'(?:Objects are not valid as a React child|Too many re-renders|Each child in a list should have a unique "key"|React has detected a change in the order of Hooks)', 'React reported a rendering or component-contract issue: {detail}', 'The message identifies a React rendering invariant or warning; a component stack, when present, narrows the affected component.', ['Find the first component named in the component stack.', 'Check whether render output matches the expected React child type and hook order.', 'Fix the component invariant before suppressing the warning.'], 'React relies on stable hook order and renderable child values between renders.', 'Keep rendering pure and test components with empty and populated data.'),
    ('Node.js module not found', 'Node.js', r"(?:Error: )?Cannot find module\s+[\'\"]([^\'\"]+)[\'\"]", 'Node.js could not resolve the module `{identifier}` from this process.', 'Module resolution failed for `{identifier}`. The log does not establish whether it is a missing dependency, wrong path, or install-directory mismatch.', ['Check whether `{identifier}` is a project file or a package dependency.', 'For a package, verify it appears in `package.json` and run `npm install` in the project root.', 'For a local module, check the relative path and filename casing.'], 'Node resolves local paths relative to the importing file and packages from node_modules.', 'Commit lockfiles and run installs from the documented project root.'),
    ('MySQL access denied', 'MySQL', r'Access denied for user\s+[\'\"]?([^\'\"@\s]+)[\'\"]?@?[\'\"]?([^\'\"\s]+)?', 'MySQL rejected authentication or privileges for the account shown: {detail}', 'The server was reached far enough to reject the account. The log does not show whether the password, host grant, or requested privileges are wrong.', ['Confirm the application uses the expected account and host.', 'Check the account’s grants and secret configuration without printing credentials.', 'Grant only the privileges required by the application.'], 'MySQL accounts include both a username and a host pattern, and privileges are checked per account.', 'Keep credentials in a secret store and separate development and production accounts.'),
    ('Database connection failure', 'Databases', r"(?:ECONNREFUSED|connection refused|could not connect to server|Can't connect to MySQL server|OperationalError.*(?:connect|connection)|SQLSTATE\[08001\]|MySQL.*timed out)", 'The application could not establish a connection to the database service: {detail}', 'The log shows a connection failure, not an authentication failure. It does not prove whether the service is stopped, the address is wrong, or a network rule blocked it.', ['Check that the database service is running and listening.', 'Verify the configured host, port, and container/network mapping.', 'Check firewall and service logs before changing credentials.'], 'Database connection setup happens before query permissions or SQL execution.', 'Add a health check and keep connection settings environment-specific.'),
    ('SQL syntax error', 'Databases', r'(?:SQL syntax|syntax error at or near|You have an error in your SQL syntax)', 'The database parser rejected the SQL statement near the reported token: {detail}', 'This is a query parsing error. The exact cause needs the query text and database dialect; the nearest token is a clue, not always the source of the mistake.', ['Inspect the complete query and the token or position named by the database.', 'Check quoting, commas, reserved words, and dialect-specific syntax.', 'Use parameterized queries for values and run the corrected statement in a safe test environment.'], 'SQL dialects differ, and the parser often reports where it noticed invalid syntax rather than where it began.', 'Test queries against the same database engine and version used by the application.'),
    ('Git merge conflict', 'Git / GitHub', r'(?:CONFLICT \(.*\)|both modified:|merge conflict)', 'Git found overlapping changes that it cannot merge automatically: {detail}', 'The named file or conflict marker identifies work that requires a deliberate choice; Git has not decided which version is correct.', ['Run `git status` and open each conflicted file.', 'Resolve the `<<<<<<<`, `=======`, and `>>>>>>>` sections using the intended changes.', 'Run relevant tests, then stage the resolved files and continue the merge.'], 'A merge conflict occurs when branches changed overlapping parts of a file.', 'Merge or rebase frequently and test before completing the integration.'),
    ('Git authentication failure', 'Git', r'(?:Authentication failed|Permission denied \(publickey\)|HTTP Basic: Access denied)', 'Git could not authenticate to the remote repository: {detail}', 'The remote rejected the supplied authentication method or account. The message does not justify embedding credentials in a remote URL.', ['Confirm the remote URL and account access.', 'Refresh the approved credential or SSH key using your credential manager.', 'Retry without pasting tokens into commands, logs, or chat.'], 'Git hosting providers authenticate HTTPS and SSH remotes differently.', 'Use a credential manager or SSH agent and rotate exposed credentials.'),
    ('npm dependency conflict', 'npm', r'ERESOLVE|unable to resolve dependency tree', 'npm could not find a compatible set of package versions: {detail}', 'The ERESOLVE report names packages whose declared version requirements conflict.', ['Read the complete ERESOLVE report and identify the conflicting package versions.', 'Choose compatible versions based on the project’s supported framework version.', 'Update package.json deliberately and regenerate the lockfile; avoid `--force` unless you understand the risk.'], 'npm resolves a dependency graph whose packages declare version ranges.', 'Commit the lockfile and test upgrades in a separate change.'),
    ('npm package failure', 'Build / deployment', r'npm ERR!|npm error', 'npm failed during the package operation shown in the log: {detail}', 'The first npm error code and package name are more useful than later summary lines; this log should be checked for the earliest diagnostic.', ['Read the earliest `npm ERR!` or `npm error` line for the code and package.', 'Check the working directory, Node/npm version, and lockfile state.', 'Use the specific npm command indicated by the error only after confirming the cause.'], 'npm output often repeats the final failure after the underlying resolver or lifecycle error.', 'Use supported Node versions and reproducible lockfile-based installs.'),
    ('pip package failure', 'Python / pip', r'(?:No matching distribution found for|Could not find a version that satisfies the requirement)\s*([^\s;]+)?', 'pip could not find an installable distribution matching `{identifier}` for this environment.', 'The package index, version constraint, Python version, and platform can all affect availability; the message alone does not prove the package name is wrong.', ['Check the package’s published distribution name and the requested version.', 'Confirm the active Python version and platform are supported.', 'Use `python -m pip index versions PACKAGE` or the package documentation to inspect available versions.'], 'pip selects distributions based on version constraints, Python compatibility, and platform tags.', 'Pin supported versions and install through the project virtual environment.'),
    ('Docker build failure', 'Docker', r'(?:failed to solve|failed to build|ERROR \[.*\]|executor failed running|Docker container exited)', 'Docker could not complete the build step shown in the log: {detail}', 'The first failed build step is the key evidence; later BuildKit messages may only repeat its failure.', ['Find the earliest failed Dockerfile step and read its command output.', 'Check the build context, copied files, base image, and command used by that step.', 'Rebuild after correcting that step; do not infer container runtime behavior from a build failure.'], 'A Docker image build executes ordered Dockerfile instructions against a build context.', 'Keep builds reproducible and avoid copying secrets into image layers.'),
    ('HTTP 401', 'HTTP / REST', r'(?:HTTP/\S+\s+401|\b401\s+Unauthorized|Unauthorized)', 'The HTTP service rejected the request because it did not accept the supplied authentication credentials.', 'A 401 response indicates authentication was missing, invalid, or expired; it does not by itself identify which credential is wrong.', ['Check whether the request includes the expected authentication scheme.', 'Confirm the credential is current and intended for this environment.', 'Refresh or rotate credentials through the approved secure flow.'], 'HTTP 401 concerns authentication; authorization is normally evaluated after identity is established.', 'Handle token expiry explicitly and never log credential values.'),
    ('HTTP 403', 'HTTP / REST', r'(?:HTTP/\S+\s+403|\b403\s+Forbidden|Forbidden)', 'The HTTP service understood the request but refused access to the requested resource.', 'A 403 response indicates an access policy or permission decision; it does not mean the route is absent.', ['Confirm which identity the server authenticated.', 'Check the resource policy, role, and required permission.', 'Request only the minimum permission needed.'], 'HTTP 403 differs from 401: the server is refusing access rather than asking for accepted authentication.', 'Test authorization rules for each role.'),
    ('HTTP 404', 'HTTP / REST', r'(?:HTTP/\S+\s+404|\b404\s+Not Found)', 'The HTTP service returned 404 for the requested resource: {detail}', 'The status confirms that this server did not find the requested route or resource. It does not establish whether the URL is misspelled or the resource is absent.', ['Compare the exact method and URL with the server route configuration.', 'Confirm the request reached the intended host and environment.', 'If the route exists, check any path prefix or resource identifier.'], 'HTTP 404 describes a missing route or resource from the server’s point of view.', 'Keep API base paths centralized and test URL resolution.'),
    ('HTTP 500', 'HTTP / REST', r'(?:HTTP/\S+\s+500|\b500\s+Internal Server Error|Internal Server Error)', 'The server reported an internal error while handling the request.', 'The client log confirms a server-side failure response, but the root cause is in the server logs or trace for the same request.', ['Find the matching server-side exception using the timestamp or request ID.', 'Inspect the first application frame and relevant upstream/database events.', 'Fix and verify the server failure before retrying the request.'], 'HTTP 500 is a response category, not a diagnosis of the underlying server exception.', 'Log request IDs and return safe error responses while preserving detailed server logs.'),
    ('HTTP error', 'HTTP / REST', r'HTTP/\S+\s+([45]\d\d)|\b([45]\d\d)\s+([A-Za-z ]+)', 'The service returned HTTP {identifier}: {detail}', 'The status code establishes the response category. More context is needed to identify the responsible component or cause.', ['Inspect the request method, URL, response body, and matching server log.', 'Use the specific status meaning to check authentication, permissions, route, or server behavior.', 'Correlate by timestamp or request ID before retrying.'], 'HTTP status codes describe the result of an HTTP request at the protocol level.', 'Record request IDs and test status handling in clients.'),
    ('Linux permission error', 'Linux / UNIX', r'(?:Permission denied|Operation not permitted)', 'The operating system denied access to the named file, command, or resource: {detail}', 'The message proves an access check failed. It does not establish that running as administrator is appropriate.', ['Check the exact path and the current user.', 'Inspect ownership and mode with `ls -l PATH` or the relevant resource policy.', 'Grant the narrow permission needed rather than running the entire application as root.'], 'Unix permissions are checked against the process identity and resource access mode.', 'Use least privilege and document required file permissions.'),
    ('Network connection failure', 'Networking', r'(?:ECONNREFUSED|ETIMEDOUT|timed out|Name or service not known|Temporary failure in name resolution|connection reset)', 'The client could not complete the network connection described by the log: {detail}', 'This establishes a transport or name-resolution failure; it does not alone identify which network hop failed.', ['Check the target hostname and port.', 'Verify that the target service is listening and reachable from this machine or container.', 'Use the specific error code to distinguish refusal, timeout, reset, and DNS failure.'], 'A network request can fail during name resolution, connection setup, or data transfer.', 'Add bounded retries only for transient operations and capture request timing.'),
    ('Deployment failure', 'Build / deployment', r'(?:deployment failed|deploy failed|release failed|health check failed|build failed)', 'The deployment or build process reported a failure: {detail}', 'This line identifies the deployment stage as failed, but the first preceding command or health-check error is needed to establish why.', ['Find the earliest failed build command or deployment health check.', 'Check the deployment environment, artifact, and required configuration.', 'Compare the failing release with the last successful release before changing production settings.'], 'A deployment combines build, configuration, rollout, and health checks; a final failure can mask an earlier stage.', 'Keep release logs and use staged rollouts with explicit health checks.'),
]


def _rule_for(text):
    for name, technology, pattern, summary, cause, steps, concept, prevention in RULES:
        if name == 'Python TypeError' and re.search(r'TypeError:\s*Cannot read properties', text, re.I):
            continue
        match = re.search(pattern, text, re.I | re.M)
        if match:
            return {'name': name, 'technology': technology, 'match': match, 'pattern': pattern, 'summary': summary,
                    'cause': cause, 'steps': steps, 'concept': concept, 'prevention': prevention}
    return None


def _location(line):
    patterns = [
        r'File [\'\"]([^\'\"]+)[\'\"], line (\d+)(?:, in ([^\s]+))?',
        r'\bat\s+([\w.$]+)\(([^():]+):(\d+)\)',
        r'((?:[A-Za-z]:[\\/]|/|\.\.?/)?[\w./\\-]+\.(?:py|js|jsx|ts|tsx|java|c|cpp|cs|sql)):(\d+)',
        r'\bline\s+(\d+)\b',
    ]
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, line, re.I)
        if not match:
            continue
        if index == 0:
            return {'file_path': match.group(1), 'line_number': int(match.group(2)), 'function': match.group(3)}
        if index == 1:
            return {'file_path': match.group(2), 'line_number': int(match.group(3)), 'function': match.group(1)}
        if index == 2:
            return {'file_path': match.group(1), 'line_number': int(match.group(2)), 'function': None}
        return {'file_path': None, 'line_number': int(match.group(1)), 'function': None}
    return {'file_path': None, 'line_number': None, 'function': None}


def _format_rule(rule, raw, identifier):
    match = rule['match']
    groups = [item for item in match.groups() if item]
    detail = (groups[-1] if groups else raw).strip().rstrip('.')
    value = {'identifier': identifier or detail or raw, 'detail': detail or raw}
    return value


def _explain_non_traceback(log_text, level='beginner', language='en'):
    """Return a structured, evidence-anchored interpretation without claiming external AI."""
    lines = log_text.splitlines()
    if log_text.endswith(('\n', '\r')):
        lines.append('')
    rule = _rule_for(log_text)
    rule_match = rule['match'] if rule else None
    groups = [item for item in rule_match.groups() if item] if rule_match else []
    identifier = groups[0] if groups else None
    detail = (groups[-1] if groups else '')
    main_index = None
    if rule:
        for index, line in enumerate(lines):
            if re.search(rule['pattern'], line, re.I):
                main_index = index
        if main_index is None:
            main_index = next((i for i, line in enumerate(lines) if line.strip()), 0)

    locations = [_location(line) for line in lines]
    error_type = rule['name'] if rule else None
    severity_match = re.search(r'\b(TRACE|DEBUG|INFO|NOTICE|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b', log_text, re.I)
    severity = 'ERROR' if rule else (severity_match.group(1).upper() if severity_match else 'INFO')
    technologies = [rule['technology']] if rule else []
    if rule and rule['technology'] == 'Docker': technologies = ['Docker / containers']
    if rule and rule['technology'] == 'Git': technologies = ['Git / GitHub']
    if rule and rule['technology'] == 'npm': technologies = ['Build / deployment']
    if rule and rule['technology'] in ('Python', 'Django'):
        technologies = ['Python / Django']
    if rule and rule['technology'] == 'Python / pip':
        technologies = ['Python / pip']

    if rule:
        values = _format_rule(rule, lines[main_index] if lines else '', identifier)
        quick_summary = rule['summary'].format(**values)
        root_confirmed = rule['cause'].format(**values)
        fix_steps = [step.format(**values) for step in rule['steps']]
        learning_concept = rule['concept']
        prevention = rule['prevention']
        confidence = 0.9 if rule['name'] in ('Python NameError', 'Python ZeroDivisionError', 'Java NullPointerException', 'Django 404', 'HTTP 401', 'HTTP 403', 'HTTP 500') else 0.78
        classification = ['ERROR']
        if re.search(r'\bWARN(?:ING)?\b', log_text, re.I):
            classification = ['WARNING', 'ERROR', 'MIXED']
        evidence_lines = [main_index + 1] if lines else []
        cause_uncertainty = 'The logged error is identified, but upstream conditions may still need confirmation.'
        if rule['name'] == 'Django missing table':
            cause_uncertainty = 'Possible reasons the table is absent include unapplied migrations, using a different database/schema than expected, or a model/app migration configuration issue. The log does not distinguish among these possibilities.'
    else:
        first_line = next((line.strip() for line in lines if line.strip()), '')
        levels = []
        for marker, label in ((r'\b(?:TRACE|DEBUG)\b', 'DEBUG'), (r'\bINFO\b|\b(?:started|listening|connected|completed|success)\b', 'INFO'), (r'\bWARN(?:ING)?\b|\b(?:deprecated|retrying)\b', 'WARNING'), (r'\b(?:ERROR|FATAL|CRITICAL)\b', 'ERROR')):
            if re.search(marker, log_text, re.I): levels.append(label)
        classification = levels or ['INFO']
        if len([level for level in levels if level in ('WARNING', 'ERROR')]) > 1:
            classification.append('MIXED')
        severity = 'ERROR' if 'ERROR' in levels else 'WARNING' if 'WARNING' in levels else 'INFO'
        quick_summary = (f'Log type cannot be identified confidently from the supplied text: “{first_line[:180]}”.' if first_line else 'The log is empty.')
        root_confirmed = 'The supplied lines do not contain a recognized error signature.'
        cause_uncertainty = 'I could not confidently identify a root cause from this log. The lines below describe only what is present; include the preceding and following events for more context.'
        confidence = 0.25
        evidence_lines = []
        fix_steps = ['No correction is suggested because this log does not establish a failure.', 'If an operation failed, include its exact error and the events immediately before it.']
        learning_concept = 'A log line is evidence about an event, but an informational message alone is not proof of a failure.'
        prevention = 'Keep the full message, timestamp, component, and nearby events together when investigating a problem.'

    records = []
    for index, line in enumerate(lines):
        low = line.lower()
        role = 'context'
        line_severity = 'context'
        if index == main_index and rule:
            role, line_severity = 'root_cause', 'error'
            line_text = quick_summary
            if rule['name'] == 'Python NameError' and identifier:
                line_text = f'Python could not find `{identifier}` when this statement ran. Check its spelling, definition and scope.'
            elif rule['name'] == 'Python ZeroDivisionError':
                line_text = 'The division operation reached a zero divisor.'
            elif rule['name'] == 'Python IndexError':
                line_text = f'The sequence access failed: {detail or line.strip()}.'
            elif rule['name'] == 'Python ModuleNotFoundError':
                line_text = f'The active Python interpreter could not import `{identifier}`.'
            elif rule['name'] == 'Python TypeError':
                line_text = f'Python rejected this operation: {detail}.'
            elif rule['name'] == 'Java NullPointerException':
                line_text = 'Java code dereferenced a null object reference.'
            elif rule['name'] == 'Django 404':
                line_text = f'Django returned a 404 for the requested path: {line.strip()}.'
            elif rule['name'] == 'HTTP 401':
                line_text = 'The server did not accept the request credentials.'
            elif rule['name'] == 'HTTP 403':
                line_text = 'The server refused this request because access is not permitted.'
            elif rule['name'] == 'HTTP 500':
                line_text = 'The server reported an internal error while handling this request.'
        elif re.search(r'^\s*Traceback \(most recent call last\):|^\s*Caused by:', line, re.I):
            role, line_severity = 'trace_start', 'context'
            line_text = 'This line starts an exception chain; the final exception names the failure, while frames show how execution reached it.'
        elif locations[index]['file_path'] and rule and ('traceback' in log_text.lower() or ' at ' in line):
            role, line_severity = 'stack_frame', 'context'
            location = locations[index]
            line_text = f"Stack frame in {location['file_path']}" + (f" at line {location['line_number']}" if location['line_number'] else '') + (f" inside {location['function']}" if location['function'] else '') + '. It shows a point in the call path, not necessarily the original cause.'
        elif re.search(r'\b(WARN(?:ING)?|deprecated|retrying)\b', line, re.I):
            role, line_severity = 'warning', 'warning'
            line_text = f'This warning records: “{line.strip()}”. It may be related, but the line alone does not show that it caused the failure.'
        elif re.search(r'\b(INFO|started|listening|connected|completed successfully)\b', line, re.I):
            role, line_severity = 'informational', 'info'
            line_text = f'This informational line records the event “{line.strip()}”; it is not an error by itself.'
        elif rule:
            role, line_severity = 'supporting', 'context'
            line_text = f'This line provides context for {rule["name"]}: “{line.strip()}”. Compare its timestamp and component with the error line.'
        else:
            line_text = f'No known failure marker is present on this line: “{line.strip()}”. It is retained as context, not treated as a confirmed cause.'
        records.append({
            'number': index + 1, 'original': line,
            'timestamp': (re.search(r'\b\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?', line) or [None])[0],
            'severity': line_severity, 'role': role,
            'component': (re.search(r'\[([\w./:-]+)\]', line) or [None, None])[1],
            'error_code': (re.search(r'\b(?:ECONNREFUSED|SQLSTATE\[[^]]+\]|[A-Z]{2,}[_-]\d{2,}|[45]\d\d)\b', line) or [None])[0],
            **locations[index], 'explanation': line_text,
        })

    confirmed = root_confirmed if rule else None
    possible = []
    if rule:
        possible.append({'cause': cause_uncertainty, 'evidence_lines': evidence_lines})
    else:
        possible.append({'cause': cause_uncertainty, 'evidence_lines': [row['number'] for row in records if row['original'].strip()]})
    terms = []
    glossary = {
        'NameError': 'Python could not find a variable or name in the active scope.',
        'KeyError': 'A mapping lookup requested a key that was not available at that moment.',
        'TypeError': 'An operation received a value whose type does not support that operation.',
        'IndexError': 'A sequence position was outside the available indexes.',
        'ZeroDivisionError': 'A division operation reached a zero divisor.',
        'ModuleNotFoundError': 'Python could not import a module in the active environment.',
        'NullPointerException': 'Java code tried to use a null object reference.',
        'ReferenceError': 'JavaScript could not resolve a referenced name.',
        'ECONNREFUSED': 'A connection was refused by the target host or service.',
        'SQLSTATE': 'A standardized database condition code.',
        'ERESOLVE': 'npm could not resolve compatible dependency versions.',
        'HTTP 401': 'The request was not accepted as authenticated.',
        'HTTP 403': 'The server refused access to the requested resource.',
        'HTTP 404': 'The requested route or resource was not found.',
        'HTTP 500': 'The server reported an internal error.',
    }
    for term, definition in glossary.items():
        if term.lower() in log_text.lower():
            terms.append({'term': term, 'definition': definition if language == 'en' else f'{term}: ತಾಂತ್ರಿಕ ದೋಷದ ಗುರುತು. ಮೂಲ ಸಂದೇಶದಲ್ಲಿನ ಹೆಸರುಗಳು ಮತ್ತು ಕೋಡ್ ಹಾಗೆಯೇ ಉಳಿಸಲಾಗಿದೆ.'})
    where = [{'line': row['number'], 'file_path': row['file_path'], 'line_number': row['line_number'], 'function': row['function']} for row in records if row['file_path'] or row['line_number']]
    if level == 'advanced' and rule:
        quick_summary += ' This is local pattern analysis; it does not execute the program or verify the environment.'
    elif level == 'beginner' and language == 'kn' and rule:
        quick_summary = f"{rule['name']} ದೋಷ: {identifier or detail or 'ಲಾಗ್‌ನಲ್ಲಿ ಕಂಡ ದೋಷ'}. {root_confirmed}"
    elif language == 'kn' and not rule:
        quick_summary = f'ಲಾಗ್‌ನಲ್ಲಿ ಗುರುತಿಸಲಾದ ದೋಷ ಕಂಡುಬಂದಿಲ್ಲ. ಮೂಲ ಸಾಲು: “{next((line.strip() for line in lines if line.strip()), "ಖಾಲಿ ಲಾಗ್")[:160]}”.'
    return {
        'provider': 'Local LogSense', 'source': 'local_patterns', 'status': 'partial' if not rule else 'complete',
        'original_log': log_text, 'quick_summary': quick_summary, 'what_happened': quick_summary,
        'why': confirmed or cause_uncertainty, 'classification': classification, 'error_type': error_type or 'Unknown / informational',
        'severity': severity, 'technologies': technologies, 'identifier': identifier,
        'database_engine': ('SQLite' if re.search(r'\b(?:sqlite3|SQLite|no such table:)', log_text, re.I) else 'MySQL' if re.search(r'\bMySQL|mysql\.', log_text, re.I) else 'PostgreSQL' if re.search(r'\bPostgreSQL|psycopg|relation\s+["\']', log_text, re.I) else None),
        'database_table': identifier if error_type == 'Django missing table' else None,
        'exception_type': (re.search(r'\b(?:django\.db\.(?:utils|migrations\.exceptions)\.)?(?:OperationalError|ProgrammingError|InconsistentMigrationHistory|MigrationConflict)\b', log_text) or [None])[0],
        'line_explanations': records, 'technical_terms': terms,
        'root_cause': {'confirmed': confirmed, 'likely': cause_uncertainty if rule else None, 'possible': possible,
                       'confidence': confidence, 'evidence_lines': evidence_lines,
                       'uncertainty': cause_uncertainty},
        'where': where, 'impact': 'Impact is not established by the supplied log alone.',
        'fix_steps': fix_steps, 'correct_example': None,
        'expected_result': 'Verify the suggested change by reproducing the operation and checking that this specific error no longer appears.',
        'prevention': prevention, 'learning_concept': learning_concept,
        'next_steps': ['Inspect the evidence lines above and correlate them with the same timestamp or request.',
                       'If the cause remains uncertain, include the preceding and following log events.'],
        'explanation_level': level, 'language': language,
    }


_TRACEBACK_START = re.compile(r'Traceback \(most recent call (?:last|first)\):', re.I)
_TRACEBACK_EXCEPTION = re.compile(
    r'^(?P<exception_type>(?:[A-Za-z_]\w*\.)*[A-Z][A-Za-z0-9_]*)'
    r'(?::\s*(?P<message>.*))?$'
)


def _parse_python_tracebacks(log_text):
    lines = log_text.splitlines()
    starts = [index for index, line in enumerate(lines) if _TRACEBACK_START.search(line)]
    tracebacks = []
    for position, start in enumerate(starts):
        stop = starts[position + 1] if position + 1 < len(starts) else len(lines)
        exception_index = None
        exception_type = None
        message = ''
        for index in range(start + 1, stop):
            raw_line = lines[index]
            if raw_line[:1].isspace():
                continue
            candidate = raw_line.strip()
            if re.match(r'^(?:TRACE|DEBUG|INFO|NOTICE|WARN(?:ING)?)\s*:', candidate):
                continue
            prefix = re.match(r'^(?:ERROR|CRITICAL|FATAL)\s*[:\]-]\s*(.+)$', candidate, re.I)
            if prefix:
                candidate = prefix.group(1)
            match = _TRACEBACK_EXCEPTION.match(candidate)
            if match:
                exception_index = index
                exception_type = match.group('exception_type').rsplit('.', 1)[-1]
                message = (match.group('message') or '').strip()
                break

        frame_locations = []
        frame_indexes = []
        frame_stop = exception_index if exception_index is not None else stop
        for index in range(start + 1, frame_stop):
            location = _location(lines[index])
            if location['file_path'] or location['line_number']:
                frame_indexes.append(index)
                frame_locations.append(location)

        tracebacks.append({
            'start_index': start,
            'stop_index': stop,
            'exception_index': exception_index,
            'exception_type': exception_type,
            'message': message,
            'frame_indexes': frame_indexes,
            'frames': frame_locations,
            'location': frame_locations[-1] if frame_locations else {
                'file_path': None, 'line_number': None, 'function': None,
            },
        })
    return lines, tracebacks


def _python_exception_diagnosis(traceback):
    exception_type = traceback['exception_type']
    message = traceback['message']
    location = traceback['location']
    line_number = traceback['exception_index'] + 1 if traceback['exception_index'] is not None else None
    location_text = ''
    if location['file_path']:
        location_text = location['file_path']
        if location['line_number'] is not None:
            location_text += f":{location['line_number']}"
        if location['function']:
            location_text += f" in {location['function']}"
    elif location['line_number'] is not None:
        location_text = f"line {location['line_number']}"

    if not exception_type:
        summary = 'A Python traceback was detected, but its final exception line is missing.'
        confirmed = 'The supplied text contains a Python traceback header, but no final exception type or message.'
        likely = 'The log may be truncated before Python printed the exception. The failure itself cannot be identified without that final line.'
        steps = ['Include the traceback through its final exception line.', 'Use the last `File ..., line ...` frame to inspect the operation that failed.']
        label = 'Incomplete Python traceback'
        explanation = confirmed
        identifier = None
        confidence = 0.35
    else:
        label = f'Python {exception_type}'
        suffix = f' at {location_text}' if location_text else ''
        actual_message = message or 'no exception message was included'
        identifier = None
        confidence = 0.82

        if exception_type == 'KeyError':
            identifier = message
            summary = f'Python could not find the requested key {message or "(key not shown)"} in a mapping{suffix}.'
            confirmed = f'The traceback ends with KeyError{f": {message}" if message else ""}; the requested lookup failed.'
            likely = f'The mapping did not contain {message or "the requested key"} at lookup time. The traceback does not establish whether the key was misspelled, omitted from input, or removed earlier.'
            steps = [
                f'Inspect the mapping and requested key at {location_text}.' if location_text else 'Inspect the mapping and requested key at the final traceback frame.',
                'Check the key spelling and confirm the input data contains that key.',
                'If a missing key is valid, handle that case explicitly with a fallback or `.get()`; otherwise validate the required key before lookup.',
            ]
            explanation = f'KeyError means Python tried to read key {message or "(not shown)"} from a mapping and that lookup failed.'
            confidence = 0.9
        elif exception_type == 'NameError':
            name_match = re.search(r"name\s+(['\"])(.+?)\1\s+is not defined", message)
            identifier = name_match.group(2) if name_match else None
            summary = f'Python could not resolve {identifier!r} when this code ran{suffix}.' if identifier else f'Python raised NameError: {actual_message}{suffix}.'
            confirmed = f'The traceback confirms that {identifier!r} was not defined in the active scope.' if identifier else f'The traceback ends with NameError: {actual_message}.'
            likely = 'The name may be misspelled, not assigned yet, or outside the current scope; the traceback does not distinguish which.'
            steps = [
                f'Check the spelling and capitalization of {identifier!r}.' if identifier else f'Read the NameError message: {message or "no message was provided"}.',
                'Define or import the name before this line, or pass it into the function if it belongs to another scope.',
            ]
            explanation = f'Python could not find {identifier!r} in the active scope.' if identifier else f'Python could not resolve this name: {actual_message}.'
            confidence = 0.9
        elif exception_type == 'TypeError':
            unsupported = re.search(
                r'unsupported operand type\(s\) for\s+(.+?):\s*[\'"]([^\'"]+)[\'"]\s+and\s+[\'"]([^\'"]+)[\'"]',
                message,
            )
            missing_argument = re.search(r"missing \d+ required positional argument[s]?:\s*['\"]([^'\"]+)", message)
            if unsupported:
                operator, left_type, right_type = unsupported.groups()
                summary = f'Python cannot apply {operator} to values of type {left_type} and {right_type}{suffix}.'
                explanation = f'The TypeError names incompatible operands for {operator}: {left_type} and {right_type}.'
                likely = f'The operation received a {left_type} and a {right_type}; at least one value may not have the type this operation expects.'
                steps = [
                    f'Inspect both operands at {location_text}.' if location_text else 'Inspect both operands at the final traceback frame.',
                    'Confirm the intended operation; convert a value only if that conversion matches the data model.',
                    'Add input validation for the operand types and test this mixed-type case.',
                ]
            elif missing_argument:
                identifier = missing_argument.group(1)
                summary = f'Python called a function without its required `{identifier}` argument{suffix}.'
                explanation = f'The call is missing required argument `{identifier}`.'
                likely = f'The function call did not supply required argument `{identifier}`; the traceback does not show whether the caller or function signature is unexpected.'
                steps = [
                    f'Inspect the call at {location_text} and pass `{identifier}`.' if location_text else f'Inspect the final traceback frame and pass `{identifier}`.',
                    'Compare the call with the function definition and any recent signature changes.',
                ]
            else:
                summary = f'Python could not complete the operation described by this TypeError{suffix}: {actual_message}.'
                explanation = f'TypeError: {actual_message}. This message identifies the rejected operation or arguments.'
                likely = f'The values or arguments do not satisfy the operation described by `{message or exception_type}`; inspect them at the failing frame.'
                steps = [
                    f'Inspect the values and arguments at {location_text}.' if location_text else 'Inspect the values and arguments at the final traceback frame.',
                    f'Compare them with the operation or function requirements stated in: {message or "the TypeError"}.',
                    'Validate inputs or correct the call; convert types only when that matches the intended behavior.',
                ]
            confirmed = f'The traceback confirms a TypeError with this message: {message or "(message not shown)"}'
        elif exception_type == 'IndexError':
            summary = f'Python tried to access an index that is outside the available sequence{suffix}: {actual_message}.'
            confirmed = f'The traceback confirms an invalid sequence access: {actual_message}.'
            likely = 'The requested index is outside the sequence bounds at that moment; the log does not establish why the sequence was empty or shorter than expected.'
            steps = [
                f'Inspect the sequence length and index at {location_text}.' if location_text else 'Inspect the sequence length and index at the final traceback frame.',
                'Check loop bounds and whether the sequence can be empty or shorter than expected.',
                'Guard the access or iterate over the sequence directly, according to the intended behavior.',
            ]
            explanation = f'IndexError means the requested sequence position is unavailable: {actual_message}.'
            confidence = 0.9
        elif exception_type == 'ZeroDivisionError':
            summary = f'Python attempted division with a zero divisor{suffix}: {actual_message}.'
            confirmed = 'The traceback confirms the divisor evaluated to zero at runtime.'
            likely = 'The denominator was zero when the operation ran; the log does not establish whether that value came from input or an earlier calculation.'
            steps = [
                f'Inspect the denominator at {location_text}.' if location_text else 'Inspect the denominator at the final traceback frame.',
                'Decide how a zero denominator should be handled for this calculation.',
                'Add a zero check or use a domain-appropriate alternative before dividing.',
            ]
            explanation = 'ZeroDivisionError means the calculation reached a zero divisor.'
            confidence = 0.9
        else:
            summary = f'Python raised {exception_type}: {actual_message}{suffix}.'
            confirmed = f'The traceback confirms {exception_type}: {actual_message}.'
            likely = f'The failing operation is at {location_text}; inspect the operation and values shown by the final frame to determine the upstream cause.' if location_text else 'The traceback identifies the exception, but does not include enough location detail to establish its upstream cause.'
            steps = [
                f'Inspect the failing operation at {location_text}.' if location_text else 'Inspect the final application frame in the traceback.',
                f'Use the exception message `{message or exception_type}` to check the operation and its inputs.',
                'Make the smallest correction that matches the intended behavior, then reproduce the same input.',
            ]
            explanation = f'Python raised {exception_type}: {actual_message}.'

    if line_number is not None:
        evidence_lines = [line_number]
    elif traceback['start_index'] is not None:
        evidence_lines = [traceback['start_index'] + 1]
    else:
        evidence_lines = []
    return {
        'log_type': 'Python traceback',
        'error_type': label,
        'exception_type': exception_type,
        'message': message,
        'severity': 'ERROR' if exception_type else 'UNKNOWN',
        'summary': summary,
        'explanation': explanation,
        'location': location,
        'root_cause': {'confirmed': confirmed, 'likely': likely, 'possible': [likely], 'confidence': confidence},
        'fix_steps': steps,
        'identifier': identifier,
        'evidence_lines': evidence_lines,
        'traceback_start_line': traceback['start_index'] + 1,
        'traceback_end_line': traceback['stop_index'],
    }


def explain_local(log_text, level='beginner', language='en'):
    """Explain a technical log, parsing every Python traceback before generic rules."""
    lines, tracebacks = _parse_python_tracebacks(log_text)
    if not tracebacks:
        result = _explain_non_traceback(log_text, level, language)
        result['log_type'] = result['technologies'][0] if result['technologies'] else 'Technical log'
        return result

    diagnoses = [_python_exception_diagnosis(traceback) for traceback in tracebacks]
    if language == 'kn':
        for item in diagnoses:
            if item['exception_type']:
                item['summary'] = f"{item['error_type']} ದೋಷ: {item['message'] or 'ಸಂದೇಶ ಲಭ್ಯವಿಲ್ಲ'}. {item['root_cause']['confirmed']}"
            else:
                item['summary'] = 'Python traceback ಪತ್ತೆಯಾಗಿದೆ, ಆದರೆ ಅಂತಿಮ exception ಸಾಲು ಕಾಣೆಯಾಗಿದೆ.'
    base = _explain_non_traceback(log_text, level, language)
    records = base['line_explanations']
    for traceback, diagnosis in zip(tracebacks, diagnoses):
        start = traceback['start_index']
        stop = traceback['stop_index']
        frame_indexes = set(traceback['frame_indexes'])
        exception_index = traceback['exception_index']
        for index in range(start, stop):
            row = records[index]
            if index == start:
                row.update(
                    role='trace_start',
                    severity='context',
                    explanation='This line starts a Python traceback. The final exception line identifies the error; the frames show the call path.',
                )
            elif index in frame_indexes:
                location = _location(lines[index])
                row.update(
                    role='stack_frame',
                    severity='context',
                    explanation=(
                        f"Call frame in {location['file_path']}"
                        + (f" at line {location['line_number']}" if location['line_number'] else '')
                        + (f" inside {location['function']}" if location['function'] else '')
                        + '. The deepest frame is the immediate failure location; earlier frames show its callers.'
                    ),
                )
            elif index == exception_index:
                row.update(role='root_cause', severity='error', explanation=diagnosis['explanation'])
            else:
                row.update(
                    role='supporting',
                    severity='context',
                    explanation='This line is part of the traceback context; use it with the exception and stack frames above.',
                )

    summaries = [
        f"{item['exception_type'] or item['error_type']}: {item['summary']}"
        for item in diagnoses
    ]
    quick_summary = summaries[0] if len(summaries) == 1 else (
        f"Detected {len(diagnoses)} Python tracebacks: " + ' '.join(summaries)
    )
    complete = all(item['exception_type'] for item in diagnoses)
    has_errors = any(item['exception_type'] for item in diagnoses)
    all_steps = list(dict.fromkeys(step for item in diagnoses for step in item['fix_steps']))
    possible = [
        {'cause': item['root_cause']['likely'], 'evidence_lines': item['evidence_lines']}
        for item in diagnoses
    ]
    confirmed = ' '.join(item['root_cause']['confirmed'] for item in diagnoses)
    evidence_lines = list(dict.fromkeys(line for item in diagnoses for line in item['evidence_lines']))
    all_locations = [
        {
            'line': row['number'],
            'file_path': row['file_path'],
            'line_number': row['line_number'],
            'function': row['function'],
        }
        for row in records if row['file_path'] or row['line_number']
    ]
    error_types = [item['error_type'] for item in diagnoses]
    exception_types = [item['exception_type'] for item in diagnoses if item['exception_type']]
    confidence = min(item['root_cause']['confidence'] for item in diagnoses)
    base.update({
        'status': 'complete' if complete else 'partial',
        'log_type': 'Python traceback' if len(diagnoses) == 1 else 'Multiple Python tracebacks',
        'quick_summary': quick_summary,
        'what_happened': quick_summary,
        'why': confirmed,
        'classification': (['ERROR'] if has_errors else []) + ([] if complete else ['INCOMPLETE']),
        'error_type': error_types[0] if len(diagnoses) == 1 else 'Multiple Python exceptions',
        'exception_type': exception_types[0] if len(exception_types) == 1 else None,
        'exception_types': exception_types,
        'severity': 'ERROR' if has_errors else 'UNKNOWN',
        'technologies': ['Python / Django'],
        'identifier': diagnoses[0]['identifier'] if len(diagnoses) == 1 else None,
        'line_explanations': records,
        'where': all_locations,
        'root_cause': {
            'confirmed': confirmed,
            'likely': ' '.join(item['root_cause']['likely'] for item in diagnoses),
            'possible': possible,
            'confidence': confidence,
            'evidence_lines': evidence_lines,
            'uncertainty': 'Possible upstream causes are listed separately; the traceback confirms only the exception and its displayed call path.',
        },
        'fix_steps': all_steps,
        'errors': diagnoses,
        'next_steps': [
            'Inspect each final exception line and its deepest application frame.',
            'Apply the suggested fix for each error, then rerun the same input to verify it.',
        ],
    })
    return base
