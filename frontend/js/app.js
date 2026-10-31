// BugSense AI - Premium Debugging Studio
let currentSessionId = null;
let currentAttemptId = null;
let analysisResult = null;
window.monacoEditor = null;
window.pendingRepair = null;
let monacoLoaded = false;
let sidebarOpen = false;
let activeTerminalTab = 'output';
let activeProjectFiles = [];
let activeProjectFilePath = '';

const INITIAL_WORKSPACE_CODE = '# Enter or load Python code here\ndef calculate_total(price, quantity):\n    total = price * quantity\n    return total\n\nprice = 100\nquantity = 5\nprint(total_price)';

function ensureWorkspaceCode() {
    if (typeof window.bugSenseWorkspaceCode !== 'string') {
        window.bugSenseWorkspaceCode = INITIAL_WORKSPACE_CODE;
    }
    return window.bugSenseWorkspaceCode;
}

function setCurrentSessionId(id) {
    currentSessionId = id || null;
    const title = document.getElementById('workspace-session-title');
    if (title) title.textContent = currentSessionId ? `Session #${currentSessionId}` : 'New session';
}

function getEditorCode() {
    if (window.monacoEditor) {
        window.bugSenseWorkspaceCode = window.monacoEditor.getValue();
    } else {
        const fallback = document.getElementById('workspace-code-fallback');
        if (fallback) window.bugSenseWorkspaceCode = fallback.value;
        else return '';
    }
    return ensureWorkspaceCode();
}

function setEditorCode(code) {
    window.bugSenseWorkspaceCode = String(code ?? '');
    if (window.monacoEditor) window.monacoEditor.setValue(window.bugSenseWorkspaceCode);
    const fallback = document.getElementById('workspace-code-fallback');
    if (fallback) fallback.value = window.bugSenseWorkspaceCode;
}

// One AMD strategy is used consistently: the Monaco 0.45 AMD loader and its matching editor modules.
function loadMonacoEditor() {
    const container = document.getElementById('monaco-editor-container');
    if (!container) return Promise.resolve(null);
    if (window.monacoEditor?.getDomNode()?.isConnected) {
        window.monacoEditor.layout();
        return Promise.resolve(window.monacoEditor);
    }
    if (window.monacoEditor) disposeMonacoEditor();

    if (!window.__bugSenseMonacoModulesPromise) {
        window.__bugSenseMonacoModulesPromise = new Promise((resolve, reject) => {
            const loaderUrl = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs';
            const loadModules = () => {
                const amdRequire = window.require;
                if (typeof amdRequire !== 'function' || typeof amdRequire.config !== 'function') {
                    reject(new Error('The Monaco AMD loader did not initialize.'));
                    return;
                }
                amdRequire.config({ paths: { vs: loaderUrl } });
                amdRequire(['vs/editor/editor.main'], () => {
                    if (!window.monaco?.editor?.create) {
                        reject(new Error('Monaco editor modules loaded without the editor API.'));
                        return;
                    }
                    resolve();
                }, reject);
            };
            if (typeof window.require === 'function') {
                loadModules();
                return;
            }
            let script = document.querySelector('script[data-bugsense-monaco-loader]');
            if (script) script.remove();
            script = document.createElement('script');
            script.src = `${loaderUrl}/loader.min.js`;
            script.async = true;
            script.dataset.bugsenseMonacoLoader = 'true';
            script.addEventListener('load', loadModules, { once: true });
            script.addEventListener('error', () => reject(new Error('The Monaco editor loader could not be downloaded.')), { once: true });
            document.head.appendChild(script);
        }).catch((error) => {
            window.__bugSenseMonacoModulesPromise = null;
            throw error;
        });
    }
    return window.__bugSenseMonacoModulesPromise.then(() => initializeMonaco());
}

function initializeMonaco() {
    const container = document.getElementById('monaco-editor-container');
    if (!container) return null;
    if (window.monacoEditor && window.monacoEditor.getDomNode()?.isConnected) {
        window.monacoEditor.layout();
        return window.monacoEditor;
    }
    if (window.monacoEditor) disposeMonacoEditor();
    if (container && !window.monacoEditor) {
        // Ensure container has dimensions
        container.style.height = '400px';
        container.style.width = '100%';
        
        window.monacoEditor = window.monaco.editor.create(container, {
            value: ensureWorkspaceCode(),
            language: document.getElementById('language')?.value || 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            lineNumbers: 'on',
            fontSize: Number((typeof localStorage !== 'undefined' && localStorage.getItem('bugsense-editor-font-size')) || 13),
            fontFamily: 'JetBrains Mono',
            padding: { top: 16 },
        });
        window.bugSenseEditorChangeSubscription = window.monacoEditor.onDidChangeModelContent(() => {
            window.bugSenseWorkspaceCode = window.monacoEditor?.getValue() || '';
        });
        window.monacoEditor.onDidChangeModelLanguage?.(() => window.monacoEditor?.layout());
        window.monacoResizeObserver?.disconnect();
        if (typeof ResizeObserver !== 'undefined') {
            window.monacoResizeObserver = new ResizeObserver(() => window.monacoEditor?.layout());
            window.monacoResizeObserver.observe(container);
        }
        
        // Force layout after a short delay
        setTimeout(() => {
            if (window.monacoEditor) {
                window.monacoEditor.layout();
            }
        }, 100);
    }
    return window.monacoEditor;
}

function disposeMonacoEditor() {
    if (window.monacoEditor) {
        window.bugSenseWorkspaceCode = window.monacoEditor.getValue();
        window.bugSenseEditorChangeSubscription?.dispose();
        window.bugSenseEditorChangeSubscription = null;
        window.monacoEditor.dispose();
        window.monacoEditor = null;
    }
    window.monacoResizeObserver?.disconnect();
    window.monacoResizeObserver = null;
}

function showTextareaFallback(error) {
    const container = document.getElementById('monaco-editor-container');
    if (!container) return;
    disposeMonacoEditor();
    container.innerHTML = `<label class="editor-fallback-label" for="workspace-code-fallback">Plain text editor · Monaco could not load (${escapeHTML(error?.message || 'network error')})</label><textarea id="workspace-code-fallback" spellcheck="false" autocapitalize="off" autocomplete="off" aria-label="Python source code"></textarea>`;
    const fallback = document.getElementById('workspace-code-fallback');
    fallback.value = ensureWorkspaceCode();
    fallback.addEventListener('input', () => { window.bugSenseWorkspaceCode = fallback.value; });
}

// Router
function handleRoute() {
    const hash = window.location.hash || '#/dashboard';
    const app = document.getElementById('app');

    if (hash !== '#/workspace' && document.getElementById('monaco-editor-container')) {
        disposeMonacoEditor();
    }

    if (!window.auth.isAuthenticated() && hash !== '#/login' && hash !== '#/register') {
        window.location.hash = '#/login';
        return;
    }

    switch (hash) {
        case '#/login':
            renderLogin();
            break;
        case '#/register':
            renderRegister();
            break;
        case '#/dashboard':
            renderDashboard();
            break;
        case '#/workspace':
            renderWorkspace();
            break;
        case '#/logsense':
            renderLogSensePage();
            break;
        case '#/history':
            renderHistory();
            break;
        case '#/learning':
            renderLearningCentre();
            break;
        case '#/profile':
            renderProfile();
            break;
        case '#/settings':
            renderSettings();
            break;
        default:
            renderDashboard();
    }
    document.getElementById('sidebar')?.classList.remove('open');
    document.body.classList.remove('navigation-open');
    updateActiveNavItem();
}

function updateActiveNavItem() {
    const hash = window.location.hash || '#/dashboard';
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === hash) {
            item.classList.add('active');
        }
    });
}

function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[character]);
}

// Toggle Sidebar
function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open', sidebarOpen);
    }
    document.body.classList.toggle('navigation-open', sidebarOpen);
}

// Render Sidebar
function renderSidebar() {
    return `
        <button class="mobile-nav-toggle" type="button" aria-label="Open navigation" onclick="toggleSidebar()">☰</button>
        <button class="sidebar-backdrop" type="button" aria-label="Close navigation" onclick="toggleSidebar()"></button>
        <div class="sidebar" id="sidebar">
            <div class="sidebar-brand" onclick="window.location.hash='#/dashboard'">
                <span class="brand-mark">⌘</span>
                <span class="brand-copy"><strong>BugSense AI</strong><small>Debugging studio</small></span>
            </div>
            <nav class="sidebar-nav">
                <a href="#/dashboard" class="nav-item" id="nav-dashboard">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 001 1h3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                    </svg>
                    <span>Dashboard</span>
                </a>
                <a href="#/workspace" class="nav-item" id="nav-workspace">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <span>Workspace</span>
                </a>
                <a href="#/history" class="nav-item" id="nav-history">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>History</span>
                </a>
                <a href="#/logsense" class="nav-item" id="nav-logsense"><span>▤</span><span>LogSense</span></a>
                <a href="#/learning" class="nav-item" id="nav-learning">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5s3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18s-3.332.477-4.5 1.253" />
                    </svg>
                    <span>Learning Centre</span>
                </a>
                <a href="#/profile" class="nav-item" id="nav-profile">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM4 21a8 8 0 0116 0" />
                    </svg>
                    <span>Profile</span>
                </a>
                <a href="#/settings" class="nav-item" id="nav-settings">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 00-1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572-1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 001.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span>Settings</span>
                </a>
            </nav>
            <div class="sidebar-footer">
                <a href="#" onclick="window.auth.logout(); return false;" class="nav-item">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    <span>Logout</span>
                </a>
            </div>
        </div>
    `;
}

// Render Login Page
function renderLogin() {
    document.getElementById('app').innerHTML = `
        <div class="main-content">
            <div class="content-area">
                <div class="auth-card">
                    <h2>Login to BugSense AI</h2>
                    <form id="login-form" class="auth-form">
                        <div id="login-message" role="alert" aria-live="polite"></div>
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="username" required placeholder="Enter your username">
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" id="password" required placeholder="Enter your password">
                        </div>
                        <button type="submit">Login</button>
                        <div class="auth-footer">
                            Don't have an account? <a href="#/register">Register</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

    const loginNotice = sessionStorage.getItem('auth_notice');
    if (loginNotice) {
        const message = document.getElementById('login-message');
        message.textContent = loginNotice;
        message.style.color = 'var(--success, #34d399)';
        sessionStorage.removeItem('auth_notice');
    }

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            await window.api.login(username, password);
            window.location.hash = '#/dashboard';
        } catch (error) {
            const message = document.getElementById('login-message');
            message.textContent = error.message;
            message.style.color = 'var(--error, #f87171)';
        }
    });
}

// Render Register Page
function renderRegister() {
    document.getElementById('app').innerHTML = `
        <div class="main-content">
            <div class="content-area">
                <div class="auth-card">
                    <h2>Create Account</h2>
                    <form id="register-form" class="auth-form">
                        <div id="register-message" role="alert" aria-live="polite"></div>
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="username" required placeholder="Choose a username">
                        </div>
                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" id="email" required placeholder="Enter your email">
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" id="password" required placeholder="Choose a password">
                        </div>
                        <div class="form-group">
                            <label>Confirm password</label>
                            <input type="password" id="confirm-password" required placeholder="Enter your password again">
                        </div>
                        <button type="submit">Register</button>
                        <div class="auth-footer">
                            Already have an account? <a href="#/login">Login</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const submitButton = e.currentTarget.querySelector('button[type="submit"]');
        const message = document.getElementById('register-message');
        submitButton.disabled = true;
        message.textContent = '';

        try {
            await window.api.register(username, email, password, confirmPassword);
            sessionStorage.setItem('auth_notice', 'Account created. Please log in with your new username and password.');
            window.location.hash = '#/login';
        } catch (error) {
            message.textContent = error.message;
            message.style.color = 'var(--error, #f87171)';
        } finally {
            submitButton.disabled = false;
        }
    });
}

// Render Dashboard
async function renderDashboard() {
    try {
        const stats = await window.api.getDashboardStats();
        document.getElementById('app').innerHTML = `
            ${renderSidebar()}
            <div class="main-content">
                <div class="content-area">
                    <div class="dashboard-welcome">
                        <h1>Welcome to BugSense AI</h1>
                        <p>Find the bug. Understand the cause. Validate the fix.</p>
                        <div class="dashboard-actions">
                            <button onclick="window.location.hash='#/workspace'">New Debugging Session</button>
                            <button class="secondary" onclick="window.location.hash='#/logsense'">Explain a Technical Log</button>
                        </div>
                    </div>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-icon sessions">📊</div>
                            <div class="stat-info">
                                <div class="stat-label">Total Sessions</div>
                                <div class="stat-value">${stats.total_sessions || 0}</div>
                            </div>
                        </div>
                        <div class="stat-card"><div class="stat-icon sessions">⌕</div><div class="stat-info"><div class="stat-label">Analyses</div><div class="stat-value">${stats.total_analyses || 0}</div></div></div>
                        <div class="stat-card">
                            <div class="stat-icon repairs">🔧</div>
                            <div class="stat-info">
                                <div class="stat-label">Repairs Attempted</div>
                                <div class="stat-value">${stats.repairs_attempted || 0}</div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon verified">✓</div>
                            <div class="stat-info">
                                <div class="stat-label">Verified Repairs</div>
                                <div class="stat-value">${stats.verified_repairs || 0}</div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon failed">✗</div>
                            <div class="stat-info">
                                <div class="stat-label">Failed Verifications</div>
                                <div class="stat-value">${stats.failed_verifications || 0}</div>
                            </div>
                        </div>
                        <div class="stat-card"><div class="stat-icon sessions">▤</div><div class="stat-info"><div class="stat-label">Logs Explained</div><div class="stat-value">${stats.logs_explained || 0}</div></div></div>
                        <div class="stat-card"><div class="stat-icon verified">✎</div><div class="stat-info"><div class="stat-label">Learning Activities</div><div class="stat-value">${stats.learning_activities || 0}</div></div></div>
                    </div>
                    
                    <div class="section-header">
                        <h2 class="section-title">Recent Sessions</h2>
                    </div>
                    <div class="sessions-list" id="recent-sessions">
                        <div class="empty-state">
                            <div class="empty-state-icon">📂</div>
                            <p>No recent sessions yet.</p>
                            <button class="secondary" onclick="window.location.hash='#/workspace'" style="margin-top: 12px;">Start New Session</button>
                        </div>
                    </div>
                    <div class="dashboard-columns">
                      <section class="settings-card"><h2>Recent LogSense explanations</h2><div id="recent-logs" class="compact-list"><p class="text-secondary">Loading saved log explanations…</p></div></section>
                      <section class="settings-card"><h2>Recent projects</h2><div id="recent-projects" class="compact-list"><p class="text-secondary">Loading projects…</p></div></section>
                      <section class="settings-card"><h2>Learning progress</h2><p>${stats.completed_lessons || 0} completed lessons · ${stats.learning_activities || 0} saved activities</p><a href="#/learning">Continue learning</a></section>
                    </div>
                </div>
            </div>
        `;

        const recentHost = document.getElementById('recent-sessions');
        const recent = Array.isArray(stats.recent_sessions) ? stats.recent_sessions : [];
        if (recentHost && recent.length) {
            recentHost.innerHTML = recent.map(session => `
                <button class="session-card" type="button" onclick="openSession('${escapeHTML(session.id)}')">
                    <span><strong>${escapeHTML(session.language || 'Code')} debugging session</strong><small>${escapeHTML(new Date(session.created_at).toLocaleString())}</small></span>
                    <span class="status-badge">${escapeHTML(session.status || 'Saved')}</span>
                </button>
            `).join('');
        }
        const logsHost = document.getElementById('recent-logs');
        if (logsHost) logsHost.innerHTML = stats.recent_logs?.length ? stats.recent_logs.map(row => `<button class="compact-row" type="button" onclick="openSession('${escapeHTML(row.id)}')"><span>${escapeHTML(row.summary)}</span><small>${escapeHTML(new Date(row.created_at).toLocaleString())}</small></button>`).join('') : '<p class="empty-state">No LogSense explanations saved yet.</p>';
        const projectsHost = document.getElementById('recent-projects');
        if (projectsHost) projectsHost.innerHTML = stats.recent_projects?.length ? stats.recent_projects.map(row => `<div class="compact-row"><span>${escapeHTML(row.name)} <small>${escapeHTML(row.language)}</small></span><small>${escapeHTML(new Date(row.updated_at).toLocaleDateString())}</small></div>`).join('') : '<p class="empty-state">No projects have been uploaded yet.</p>';
        
        updateActiveNavItem();
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        document.getElementById('app').innerHTML = `
            ${renderSidebar()}
            <div class="main-content">
                <div class="content-area">
                    <div class="empty-content">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <p>Failed to load dashboard. Please try again.</p>
                    </div>
                </div>
            </div>
        `;
    }
}

// Render Workspace
function renderWorkspace() {
    disposeMonacoEditor();
    document.getElementById('app').innerHTML = `
        ${renderSidebar()}
        <div class="main-content">
            <div class="workspace-header">
                <div class="workspace-title">Debugging Workspace</div>
                <div class="workspace-controls">
                    <span class="session-title" id="workspace-session-title">${currentSessionId ? `Session #${escapeHTML(currentSessionId)}` : 'New session'}</span>
                    <span id="ai-provider-status" class="provider-status">Checking AI provider…</span>
                    <label class="text-secondary">AI Provider <select id="ai-provider-select" aria-label="AI Provider"><option value="gemini">Google Gemini</option><option value="openai">OpenAI</option><option value="local">Local Repair Engine</option><option value="automatic">Automatic Fallback</option></select></label>
                    <select id="language" style="width: auto;">
                        <option value="python">Python</option>
                    </select>
                </div>
            </div>
            <div class="content-area" style="padding: 16px;">
                <div class="privacy-consent">
                    <label><input id="ai-share-consent" type="checkbox"> Allow the selected external AI provider to process this source code</label>
                    <span>Source code is sent only after you enable this option. Quick Fix runs locally.</span>
                </div>
                <div class="workspace-layout">
                    <div class="editor-section">
                        <section class="workspace-explorer" id="workspace-explorer">
                          <header><button class="secondary" type="button" onclick="toggleWorkspaceExplorer()">▾ Project Explorer</button><select id="workspace-project-select" aria-label="Project"><option value="">No project selected</option></select><button class="secondary" type="button" id="new-project-btn">New project</button></header>
                          <div id="workspace-file-tree" class="workspace-file-tree"><p class="text-secondary">Select a project to browse its saved files. Source files are retained with the project.</p></div>
                          <div class="workspace-file-actions"><span id="active-file-tab">Unsaved buffer</span><button class="secondary" id="new-project-file-btn" type="button" disabled>New file</button><button class="secondary" id="save-project-file-btn" type="button" disabled>Save file</button><span id="project-file-message" role="status"></span></div>
                        </section>
                        <div class="action-toolbar">
                            <div class="toolbar-group">
                                <button id="run-code-btn" onclick="runCode()">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    Run Code
                                </button>
                                <button id="analyze-btn" onclick="analyzeCode()" class="secondary">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                    Analyze
                                </button>
                                <button id="repair-btn" onclick="repairCode()" class="secondary">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 00-1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572-1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 001.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                    Repair
                                </button>
                                <button id="heuristic-repair-btn" onclick="repairWithHeuristic()" class="secondary" style="background: var(--ai-violet); color: white; border-color: var(--ai-violet);">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                    Quick Fix
                                </button>
                                <button id="verify-btn" onclick="verifyCode()" class="secondary">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    Verify
                                </button>
                            </div>
                            <div class="toolbar-divider"></div>
                            <div class="toolbar-group">
                                <button onclick="loadExample()" class="secondary">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Load Example
                                </button>
                                <button onclick="clearError()" class="secondary">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                    Clear Error
                                </button>
                                <button onclick="clearLogs()" class="secondary">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                    Clear Logs
                                </button>
                            </div>
                        </div>
                        <div id="monaco-editor-container"></div>
                        <div class="terminal-panel">
                            <div class="terminal-tabs">
                                <button class="terminal-tab active" data-tab="output" onclick="switchTerminalTab('output')">Output</button>
                                <button class="secondary" id="explain-output-btn" onclick="explainLastOutput()" disabled>Explain This Output</button>
                                <button class="terminal-tab" data-tab="errors" onclick="switchTerminalTab('errors')">Errors</button>
                                <button class="terminal-tab" data-tab="explain" onclick="switchTerminalTab('explain')">Explain Output</button>
                                <button class="terminal-tab" data-tab="analysis" onclick="switchTerminalTab('analysis')">AI Analysis</button>
                                <button class="terminal-tab" data-tab="diff" onclick="switchTerminalTab('diff')">Repair Diff</button>
                                <button class="terminal-tab" data-tab="verification" onclick="switchTerminalTab('verification')">Verification</button>
                            </div>
                            <div class="terminal-content" id="terminal-output">No output yet. Click "Run Code" to execute.</div>
                        </div>
                    </div>
                    <div class="ai-panel">
                        <div class="ai-panel-header">
                            <div class="ai-panel-title">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                AI Diagnosis
                            </div>
                            <button class="secondary ai-collapse-button" type="button" onclick="toggleAIPanel()" aria-label="Collapse AI panel">Collapse</button>
                        </div>
                        <div class="ai-panel-content" id="ai-diagnosis-content">
                            <div class="empty-content">
                                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                <p style="font-size: 13px;">Run code and click "Analyze" to get AI-powered diagnosis</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    window.api.getAIHealth().then((health) => {
        const state = document.getElementById('ai-provider-status');
        if (state) {
            const ai = health.ai || {};
            const runner = health.execution?.status || 'unknown';
            state.textContent = `${ai.provider || 'AI'} ${ai.status || 'unavailable'} · runner ${runner}`;
            state.title = `Backend ${health.backend?.status || 'unknown'} · Static analyzer ${health.static_analyzer?.status || 'unknown'} · ${ai.model || 'No model selected'}`;
        }
    }).catch(() => {});
    window.api.getAIProviderSettings().then((prefs) => {
        const select = document.getElementById('ai-provider-select');
        if (select) select.value = prefs.mode;
    }).catch(() => {});
    document.getElementById('ai-provider-select')?.addEventListener('change', async (event) => {
        try { await window.api.updateAIProviderSettings({ mode: event.target.value }); }
        catch (error) {
            const state = document.getElementById('ai-provider-status');
            if (state) state.textContent = `Could not save provider: ${error.message}`;
        }
    });
    loadWorkspaceProjects();
    loadMonacoEditor().catch((error) => {
        showTextareaFallback(error);
    });
    document.getElementById('language')?.addEventListener('change', (event) => {
        const model = window.monacoEditor?.getModel();
        if (model && window.monaco?.editor) window.monaco.editor.setModelLanguage(model, event.target.value);
    });
    
    updateActiveNavItem();
}

function renderLogSensePage() {
    document.getElementById('app').innerHTML = `${renderSidebar()}<main class="main-content">
        <header class="workspace-header"><h1 class="workspace-title">LogSense <span class="text-secondary">· Understand any technical log</span></h1></header>
        <section class="content-area logsense-page">
            <p class="text-secondary">Paste application, operating system, database, HTTP, build, deployment, or terminal output. Local explanations are private by default; logs are never executed.</p>
            <div class="logsense-controls"><label>Explanation level <select id="ls-level"><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label>
            <label>Language <select id="ls-language"><option value="en">English</option><option value="kn">ಕನ್ನಡ (Kannada)</option></select></label></div>
            <textarea id="ls-input" class="logsense-input" aria-label="Technical log" placeholder="Paste any technical log here…" spellcheck="false"></textarea>
            <div class="logsense-actions"><label class="file-button">Upload .txt or .log<input id="ls-file" type="file" accept=".txt,.log,text/plain" hidden></label><button class="secondary" id="ls-paste" type="button">Paste</button>
            <label><input type="checkbox" id="ls-consent"> Allow redacted log text to be sent to my selected AI provider for interpretation</label>
            <button class="primary" id="ls-explain">Explain Log</button><button class="secondary" id="ls-clear">Clear</button><button class="secondary" id="ls-copy">Copy Log</button><button class="secondary" id="ls-save" disabled>Save Explanation</button></div>
            <div id="ls-status" role="status" class="text-secondary"></div><div id="ls-results"></div>
        </section></main>`;
    const input = document.getElementById('ls-input');
    const explainButton = document.getElementById('ls-explain');
    let explanationInProgress = false;
    const readLogFile = async (file) => {
        if (!/\.(txt|log)$/i.test(file.name) || file.size > 1_000_000) { document.getElementById('ls-status').textContent = 'Choose a .txt or .log file smaller than 1 MB.'; return; }
        try { input.value = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer()); document.getElementById('ls-status').textContent = `Loaded ${file.name}. Review it before explaining or enabling external AI.`; }
        catch { document.getElementById('ls-status').textContent = 'This file could not be read as valid UTF-8 text.'; }
    };
    document.getElementById('ls-file').addEventListener('change', async (event) => {
        const file = event.target.files?.[0]; if (!file) return;
        await readLogFile(file); event.target.value = '';
    });
    input.addEventListener('dragover', event => { event.preventDefault(); input.classList.add('drag-over'); });
    input.addEventListener('dragleave', () => input.classList.remove('drag-over'));
    input.addEventListener('drop', async event => { event.preventDefault(); input.classList.remove('drag-over'); const file = event.dataTransfer.files?.[0]; if (file) await readLogFile(file); });
    document.getElementById('ls-paste').onclick = async () => { const r = await window.clipboardService.readText(); if (r.ok) { input.value = r.text; document.getElementById('ls-status').textContent = 'Clipboard text pasted. Review it before explaining.'; } else document.getElementById('ls-status').textContent = r.cancelled ? 'Paste cancelled.' : r.message; };
    explainButton.onclick = async () => {
        if (explanationInProgress) return;
        if (!input.value.trim()) { document.getElementById('ls-status').textContent = 'Paste a log or upload a text file first.'; return; }
        explanationInProgress = true; explainButton.disabled = true;
        document.getElementById('ls-status').textContent = 'Explaining and saving this log to your history…';
        try {
            const result = await window.api.explainLog({log:input.value, explanation_level:document.getElementById('ls-level').value, explanation_language:document.getElementById('ls-language').value, allow_external_ai:document.getElementById('ls-consent').checked, session_id:window.logSenseSessionId || null});
            window.logSenseSessionId = result.session_id;
            window.latestLogSenseResult = result;
            renderLogSenseResult(result);
            document.getElementById('ls-save').disabled = false;
            document.getElementById('ls-save').textContent = 'Saved · View History';
            document.getElementById('ls-status').textContent = 'Explanation saved in your analysis history.';
        } catch (error) { document.getElementById('ls-status').textContent = error.message || 'LogSense could not complete the request.'; }
        finally { explanationInProgress = false; explainButton.disabled = false; }
    };
    document.getElementById('ls-clear').onclick = () => { input.value=''; document.getElementById('ls-results').replaceChildren(); document.getElementById('ls-status').textContent=''; window.logSenseSessionId=null; window.latestLogSenseResult=null; };
    document.getElementById('ls-copy').onclick = async () => { const r = await window.clipboardService.writeText(input.value); document.getElementById('ls-status').textContent = r.ok ? 'Original log copied.' : r.cancelled ? 'Copy cancelled.' : r.message; };
    document.getElementById('ls-save').onclick = () => { window.location.hash = '#/history'; };
    if (window.logSensePrefill) { input.value = window.logSensePrefill; window.logSensePrefill = ''; document.getElementById('ls-explain').click(); }
    updateActiveNavItem();
}

function toggleWorkspaceExplorer() { document.getElementById('workspace-explorer')?.classList.toggle('collapsed'); }

async function loadWorkspaceProjects(selectId = '') {
    const select = document.getElementById('workspace-project-select');
    if (!select) return;
    try {
        const projects = await window.api.getProjects();
        select.innerHTML = '<option value="">No project selected</option>' + projects.map(project => `<option value="${project.id}">${escapeHTML(project.name)}</option>`).join('');
        const chosen = selectId || localStorage.getItem('bugsense-project-id') || '';
        if (chosen && projects.some(project => String(project.id) === String(chosen))) { select.value = chosen; await openWorkspaceProject(chosen); }
    } catch (error) {
        document.getElementById('workspace-file-tree').textContent = error.message || 'Projects could not be loaded.';
    }
    select.onchange = async () => { activeProjectFiles = []; activeProjectFilePath = ''; document.getElementById('active-file-tab').textContent = 'Unsaved buffer'; document.getElementById('new-project-file-btn').disabled = !select.value; document.getElementById('save-project-file-btn').disabled = !select.value; localStorage.setItem('bugsense-project-id', select.value); if (select.value) await openWorkspaceProject(select.value); else renderWorkspaceFileTree(); };
    document.getElementById('new-project-btn').onclick = async () => {
        const name = window.prompt('Project name'); if (!name?.trim()) return;
        try { const project = await window.api.createProject({ name: name.trim(), source_type: 'paste', language: document.getElementById('language')?.value || 'python' }); localStorage.setItem('bugsense-project-id', project.id); await loadWorkspaceProjects(project.id); }
        catch (error) { const msg = document.getElementById('project-file-message'); if (msg) msg.textContent = error.message; }
    };
    document.getElementById('new-project-file-btn').onclick = async () => {
        if (!select.value) return;
        const path = window.prompt('New text file path, for example src/main.py'); if (!path?.trim()) return;
        try { await window.api.saveProjectFile(select.value, path.trim(), ''); await openWorkspaceProject(select.value, path.trim()); }
        catch (error) { document.getElementById('project-file-message').textContent = error.message; }
    };
    document.getElementById('save-project-file-btn').onclick = async () => {
        if (!select.value || !activeProjectFilePath) return;
        const button = document.getElementById('save-project-file-btn'); button.disabled = true;
        try { await window.api.saveProjectFile(select.value, activeProjectFilePath, getEditorCode()); document.getElementById('project-file-message').textContent = 'Saved'; activeProjectFiles = await window.api.getProjectFiles(select.value); renderWorkspaceFileTree(); }
        catch (error) { document.getElementById('project-file-message').textContent = error.message || 'File could not be saved.'; }
        finally { button.disabled = false; }
    };
}

async function openWorkspaceProject(projectId, selectPath = '') {
    const host = document.getElementById('workspace-file-tree'); if (host) host.textContent = 'Loading project files…';
    try {
        activeProjectFiles = await window.api.getProjectFiles(projectId);
        document.getElementById('new-project-file-btn').disabled = false;
        document.getElementById('save-project-file-btn').disabled = false;
        renderWorkspaceFileTree();
        const file = activeProjectFiles.find(item => item.path === (selectPath || activeProjectFilePath)) || activeProjectFiles[0];
        if (file) selectWorkspaceFile(file.path);
        else { activeProjectFilePath = ''; document.getElementById('active-file-tab').textContent = 'No file selected'; }
    } catch (error) { if (host) host.textContent = error.message || 'Project files could not be loaded.'; }
}

function renderWorkspaceFileTree() {
    const host = document.getElementById('workspace-file-tree'); if (!host) return;
    host.innerHTML = activeProjectFiles.length ? activeProjectFiles.map(file => `<button class="workspace-file-item ${file.path === activeProjectFilePath ? 'active' : ''}" type="button" data-file-path="${escapeHTML(file.path)}">▤ ${escapeHTML(file.path)}</button>`).join('') : '<p class="text-secondary">This project has no saved text files yet. Use New file to add one.</p>';
    host.querySelectorAll('[data-file-path]').forEach(button => button.addEventListener('click', () => selectWorkspaceFile(button.dataset.filePath)));
}

function selectWorkspaceFile(path) {
    const file = activeProjectFiles.find(item => item.path === path); if (!file) return;
    const current = activeProjectFiles.find(item => item.path === activeProjectFilePath);
    if (current && current.path !== path && getEditorCode() !== current.content && !window.confirm('Discard unsaved changes to this project file? Save it first to keep your edits.')) return;
    activeProjectFilePath = path; setEditorCode(file.content || '');
    const tab = document.getElementById('active-file-tab'); if (tab) tab.textContent = path;
    renderWorkspaceFileTree(); document.getElementById('project-file-message').textContent = '';
}

function explainLastOutput() {
    const log = window.bugSenseLastOutputLog || '';
    if (!log.trim()) return;
    window.logSensePrefill = log;
    window.logSenseSessionId = null;
    window.location.hash = '#/logsense';
}

function renderLogSenseResult(result) {
    const host = document.getElementById('ls-results');
    if (!host) return;
    const esc = escapeHTML;
    const rows = result.line_explanations || [];
    const ai = result.ai_interpretation;
    host.innerHTML = `<article class="logsense-card"><h2>Quick Summary</h2><p>${esc(result.quick_summary)}</p><div class="logsense-badges">${(result.classification||[]).map(x=>`<span>${esc(x)}</span>`).join('')} ${(result.technologies||[]).map(x=>`<span>${esc(x)}</span>`).join('')}<span>Source: ${esc(result.provider||result.source)}</span></div>
        ${result.redactions?.length?`<p class="text-warning">Sensitive values detected (${esc(result.redactions.join(', '))}). The live log remains unchanged; saved history and any external transmission use redacted values.</p>`:''}${result.consent?.required?`<p class="text-secondary">${esc(result.consent.message)}</p>`:''}
        <div class="logsense-columns"><section><h3>Original Log · click a line</h3><div class="logsense-lines">${rows.map((row,i)=>`<button type="button" class="logsense-line severity-${esc((row.severity||'context').toLowerCase())}" data-line-index="${i}"><span>${row.number}</span><code>${esc(row.original)}</code></button>`).join('')}</div></section><section><h3>Simple Explanation</h3><p id="ls-line-detail">${esc(result.quick_summary)}</p><details open><summary>Analysis detail</summary><p>${esc(result.what_happened||result.quick_summary)}</p><p>${esc(result.why||result.root_cause?.confirmed||result.root_cause?.uncertainty||'Not established from this log.')}</p><p>${esc(result.impact||'')}</p></details></section></div>
        ${ai?`<details><summary>AI interpretation · ${esc(ai.provider||ai.status)}</summary><p>${esc(ai.summary||ai.error||ai.message||'No additional interpretation returned.')}</p>${ai.possible_causes?`<pre>${esc(JSON.stringify(ai.possible_causes,null,2))}</pre>`:''}</details>`:''}
        ${result.technical_terms?.length?`<h3>Technical Terms</h3><dl>${result.technical_terms.map(x=>`<dt><code>${esc(x.term)}</code></dt><dd>${esc(x.definition)}</dd>`).join('')}</dl>`:''}
        ${result.where?.length?`<h3>Where it happened</h3><ul>${result.where.map(x=>`<li>Log line ${x.line}${x.file_path?` · ${esc(x.file_path)}`:''}${x.line_number?`:${x.line_number}`:''}</li>`).join('')}</ul>`:''}
        <h3>Root Cause</h3><p>${esc(result.root_cause?.confirmed||'Not established from this log.')}</p>${result.root_cause?.possible?.length?`<ul>${result.root_cause.possible.map(x=>`<li>${esc(x.cause)}${x.evidence_lines?` (evidence: lines ${esc(x.evidence_lines.join(', '))})`:''}</li>`).join('')}</ul>`:''}
        <h3>Step-by-Step Fix</h3><ol>${(result.fix_steps||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ol><h3>Prevention</h3><p>${esc(result.prevention)}</p><h3>Learning Concept</h3><p>${esc(result.learning_concept)}</p><h3>Next Steps</h3><ul>${(result.next_steps||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>
        ${result.correct_example?`<h3>Correct Example</h3><pre>${esc(result.correct_example)}</pre>`:''}<section class="ls-learning-recommendations" id="ls-learning-recommendations" aria-live="polite"></section><button class="secondary" id="ls-copy-explanation">Copy Explanation</button>
        <div class="logsense-actions"><button class="secondary" data-learn="why">Why did this happen?</button><button class="secondary" data-learn="fix">Show the fix</button><button class="secondary" data-learn="word">Explain a technical word</button><button class="secondary" data-learn="example">Real-world example</button><button class="secondary" data-learn="teach">Teach this concept</button><button class="secondary" data-learn="practice">Practice problem</button><button class="secondary" data-learn="quiz">Test my understanding</button></div><div id="ls-learning-response" aria-live="polite"></div>
        <div class="logsense-followup"><input id="ls-question" placeholder="Ask a follow-up about this log" aria-label="Follow-up question"><button class="secondary" id="ls-ask">Ask</button><p class="text-secondary">Follow-up questions use external AI only when the consent checkbox above is enabled.</p></div></article>`;
    host.querySelectorAll('[data-line-index]').forEach(button=>button.addEventListener('click',()=>{const row=rows[Number(button.dataset.lineIndex)];host.querySelectorAll('.logsense-line').forEach(x=>x.classList.toggle('selected',x===button));host.querySelector('#ls-line-detail').textContent=`Line ${row.number}${row.severity?` · ${row.severity}`:''}: ${row.explanation}`;}));
    window.api.getLearningRecommendations({error_type:result.error_type||'',message:result.quick_summary||'',technology:(result.technologies||[]).join(' ')}).then(data=>{const section=host.querySelector('#ls-learning-recommendations');if(!section)return;const matches=data.recommendations||[];section.innerHTML=matches.length?`<h3>Lessons related to this log</h3>${matches.map(row=>`<article class="learning-recommendation"><strong>${esc(row.lesson.error_name||row.lesson.title)}</strong><p>${esc(row.reason)}</p><button class="secondary" type="button" data-open-learning="${row.lesson.id}">Practise this error</button></article>`).join('')}`:'';section.querySelectorAll('[data-open-learning]').forEach(button=>button.addEventListener('click',()=>{window.learningRecommendedLessonId=button.dataset.openLearning;window.location.hash='#/learning';}));}).catch(()=>{});
    host.querySelector('#ls-copy-explanation')?.addEventListener('click',async()=>{const summary=[result.quick_summary,...rows.map(x=>`Line ${x.number}: ${x.explanation}`),...(result.fix_steps||[])].join('\n');const r=await window.clipboardService.writeText(summary);document.getElementById('ls-status').textContent=r.ok?'Explanation copied.':r.cancelled?'Copy cancelled.':r.message;});
    host.querySelectorAll('[data-learn]').forEach(button => button.addEventListener('click', async () => {
        const panel = host.querySelector('#ls-learning-response');
        const type = button.dataset.learn;
        const concept = result.learning_concept || 'Use the exact evidence shown above.';
        const evidence = result.quick_summary || '';
        if (type === 'why') { panel.textContent = `Evidence: ${evidence} Possible causes remain uncertain unless the log confirms them.`; return; }
        if (type === 'fix') { panel.innerHTML = `<p>${(result.fix_steps||[]).map((step,index)=>`${index+1}. ${escapeHTML(step)}`).join('<br>')}</p>${result.correct_example?`<pre>${escapeHTML(result.correct_example)}</pre>`:''}`; return; }
        if (type === 'word') {
            panel.innerHTML = '<label>Technical word <input id="ls-word-input" aria-label="Technical word"></label><button class="secondary" id="ls-word-submit">Explain</button><p id="ls-word-answer"></p>';
            panel.querySelector('#ls-word-submit').onclick = async () => {
                const word = panel.querySelector('#ls-word-input').value.trim();
                const definition = (result.technical_terms||[]).find(item=>item.term.toLowerCase()===word.toLowerCase());
                const answer = panel.querySelector('#ls-word-answer');
                if (definition) { answer.textContent = `${definition.term}: ${definition.definition}`; return; }
                if (!document.getElementById('ls-consent')?.checked) { answer.textContent = 'There is no local definition for that term. Enable source-sharing consent before asking the external provider.'; return; }
                answer.textContent = 'Asking the selected provider…';
                try { const follow=await window.api.explainLog({log:result.original_log,question:`Explain the technical term ${word} in the context of this log. Preserve it exactly.`,explanation_level:result.explanation_level,explanation_language:result.language,allow_external_ai:true,session_id:result.session_id}); answer.textContent=follow.ai_interpretation?.summary||follow.ai_interpretation?.error||'No explanation returned.'; }
                catch(error){answer.textContent=error.message;}
            };
            return;
        }
        if (type === 'example') { panel.textContent = 'A similar situation: a service can report a successful startup line and then log a later request failure. Read both in timestamp order.'; return; }
        if (type === 'teach') {
            panel.textContent = concept;
            try { await window.api.saveLearningActivity({type:'lesson',prompt:concept,answer:'Viewed',completed:true,session_id:result.session_id}); panel.textContent += ' Saved to your Learning Centre history.'; }
            catch (error) { panel.textContent += ` Progress was not saved: ${error.message}`; }
            return;
        }
        const prompt = type === 'quiz'
            ? 'In your own words: does this log prove the underlying cause, or does it only record a failure?'
            : 'Practice: identify the earliest failure line and name one additional piece of evidence that would help confirm its cause.';
        const reference = result.root_cause?.uncertainty || result.root_cause?.confirmed || 'Use the evidence and line explanations above.';
        panel.innerHTML = `<p>${escapeHTML(prompt)}</p><textarea id="ls-practice-answer" rows="3" aria-label="Your answer"></textarea><button class="secondary" id="ls-submit-practice">Save response</button>`;
        panel.querySelector('#ls-submit-practice').onclick = async () => {
            const userAnswer = panel.querySelector('#ls-practice-answer').value.trim();
            if (!userAnswer) { panel.append(document.createTextNode(' Enter an answer first.')); return; }
            try {
                await window.api.saveLearningActivity({type,prompt,answer:`Your response: ${userAnswer}\nReference point: ${reference}`,completed:true,session_id:result.session_id});
                panel.textContent = `Response saved. Compare it with the log evidence: ${reference}`;
            } catch (error) { panel.append(document.createTextNode(` Progress was not saved: ${error.message}`)); }
        };
    }));
    host.querySelector('#ls-ask').onclick=async()=>{const question=host.querySelector('#ls-question').value.trim();if(!question)return;const consent=document.getElementById('ls-consent').checked;if(!consent){host.querySelector('#ls-learning-response').textContent='Enable source sharing to ask the selected AI provider. The local explanation above remains available.';return;}host.querySelector('#ls-learning-response').textContent='Asking…';try{const follow=await window.api.explainLog({log:result.original_log,question,explanation_level:result.explanation_level,explanation_language:result.language,allow_external_ai:true,session_id:result.session_id});host.querySelector('#ls-learning-response').textContent=follow.ai_interpretation?.summary||follow.ai_interpretation?.error||'No follow-up answer was returned.';}catch(error){host.querySelector('#ls-learning-response').textContent=error.message;}};
}

// Render History
async function renderHistory() {
    document.getElementById('app').innerHTML = `${renderSidebar()}<main class="main-content"><div class="workspace-header"><div class="workspace-title">Session History</div></div><div class="content-area"><header class="page-heading"><h1>Session History</h1><p>Search and reopen your saved debugging and LogSense sessions.</p></header><form id="history-filters" class="history-filters"><input name="search" placeholder="Search errors, logs, or source" aria-label="Search sessions"><select name="status"><option value="">All statuses</option><option>CREATED</option><option>ANALYZED</option><option>REPAIRED</option><option>VERIFIED</option><option>FAILED</option></select><select name="language"><option value="">All languages</option><option value="python">Python</option><option value="javascript">JavaScript</option><option value="java">Java</option><option value="technical-log">Technical log</option></select><label>From <input name="date_from" type="date"></label><label>To <input name="date_to" type="date"></label><button class="secondary">Filter</button></form><div id="history-results"><div class="loading">Loading your sessions…</div></div></div></main>`;
    try {
        const form = document.getElementById('history-filters');
        const load = async (page = 1) => {
            const filters = Object.fromEntries(new FormData(form)); filters.page = page;
            const data = await window.api.getHistory(filters);
            const history = normalizeHistoryResponse(data);
            const host = document.getElementById('history-results');
            host.innerHTML = history.length ? `<div class="sessions-list">${history.map(session => `<article class="session-row"><div class="session-info"><div class="session-name">${escapeHTML(session.language || 'Session')} · #${escapeHTML(session.id)}</div><div class="session-meta"><span>${escapeHTML(new Date(session.created_at).toLocaleString())}</span><span>${escapeHTML(session.error_summary || session.error_message || 'No error summary saved')}</span></div></div><span class="session-status">${escapeHTML(session.verification_status || session.status || 'Saved')}</span><button class="secondary" type="button" onclick="openSession('${escapeHTML(session.id)}')">Open</button></article>`).join('')}</div><nav class="pagination"><button class="secondary" ${data.has_previous ? '' : 'disabled'} data-page="${data.page - 1}">Previous</button><span>Page ${data.page} of ${data.pages || 1} · ${data.total} sessions</span><button class="secondary" ${data.has_next ? '' : 'disabled'} data-page="${data.page + 1}">Next</button></nav>` : '<div class="empty-state">No sessions match these filters.</div>';
            host.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => load(Number(button.dataset.page))));
        };
        form.addEventListener('submit', event => { event.preventDefault(); load().catch(showHistoryError); });
        await load();
        updateActiveNavItem();
    } catch (error) {
        showHistoryError(error);
    }
}

function showHistoryError(error) { const host = document.getElementById('history-results'); if (host) host.innerHTML = `<div class="empty-state">${escapeHTML(error.message || 'History is temporarily unavailable.')}</div>`; }

function normalizeHistoryResponse(response) {
    if (Array.isArray(response)) return response;
    if (Array.isArray(response?.sessions)) return response.sessions;
    if (Array.isArray(response?.results)) return response.results;
    if (Array.isArray(response?.history)) return response.history;
    throw new Error('The history service returned an unexpected response. Please retry.');
}

// Render Settings
function renderSettings() {
    document.getElementById('app').innerHTML = `${renderSidebar()}<main class="main-content"><div class="workspace-header"><div class="workspace-title">Settings</div></div><div class="content-area settings-page">
      <header class="page-heading"><h1>Settings</h1><p>Manage AI routing and local workspace preferences.</p></header>
      <section class="settings-card"><div><h2>AI Providers</h2><p class="text-secondary">Credentials stay on the backend. This page only shows whether each provider is configured.</p></div><div id="settings-provider-state" class="provider-readiness">Checking configured providers…</div>
        <div class="settings-fields"><label>Active mode<select id="settings-ai-mode"><option value="gemini">Google Gemini</option><option value="openai">OpenAI</option><option value="local">Local Repair Engine</option><option value="automatic">Automatic Fallback</option></select></label>
        <label>Primary provider<select id="settings-ai-primary"><option value="gemini">Google Gemini</option><option value="openai">OpenAI</option></select></label><label>Secondary provider<select id="settings-ai-secondary"><option value="openai">OpenAI</option><option value="gemini">Google Gemini</option></select></label>
        <label class="settings-check"><input type="checkbox" id="settings-ai-fallback"> Allow fallback to secondary provider</label></div><p id="settings-ai-message" role="status" aria-live="polite"></p><button class="primary" id="save-ai-settings">Save provider settings</button>
      </section>
      <section class="settings-card"><h2>Privacy and Consent</h2><p>External providers receive source only after you enable consent for an AI operation. LogSense stores redacted logs in history.</p></section>
      <section class="settings-card"><h2>Appearance</h2><p>Choose a theme for this browser.</p><label>Theme<select id="settings-theme"><option value="dark">Dark</option><option value="light">Light</option></select></label></section>
      <section class="settings-card"><h2>Editor Preferences</h2><label>Font size <select id="settings-font-size"><option>12</option><option>13</option><option>14</option><option>15</option><option>16</option><option>18</option></select></label><p>Editor settings are stored in this browser.</p></section>
      <section class="settings-card"><h2>Language</h2><p>Interface language: English. LogSense explanation language can be selected on the LogSense page.</p></section>
      <section class="settings-card"><h2>Account and Security</h2><p>Password changes are not currently supported by this account API.</p><a href="#/profile">Manage profile</a></section>
    </div></main>`;
    const message = document.getElementById('settings-ai-message');
    window.api.getAIProviderSettings().then((p) => {
        document.getElementById('settings-ai-mode').value = p.mode;
        document.getElementById('settings-ai-primary').value = p.primary_provider;
        document.getElementById('settings-ai-secondary').value = p.secondary_provider;
        document.getElementById('settings-ai-fallback').checked = p.automatic_fallback;
        const status = p.provider_status || {};
        document.getElementById('settings-provider-state').innerHTML = `<span>Active: <b>${escapeHTML(p.active_provider || p.mode)}</b></span><span>Gemini: ${status.gemini ? 'Configured' : 'Not configured'}</span><span>OpenAI: ${status.openai ? 'Configured' : 'Not configured'}</span>`;
    }).catch((error) => { message.textContent = error.message || 'Provider preferences could not be loaded. Check your login and backend connection.'; message.className = 'form-message error'; });
    document.getElementById('save-ai-settings').onclick = async () => {
        try { const p = await window.api.updateAIProviderSettings({ mode: document.getElementById('settings-ai-mode').value, primary_provider: document.getElementById('settings-ai-primary').value, secondary_provider: document.getElementById('settings-ai-secondary').value, automatic_fallback: document.getElementById('settings-ai-fallback').checked }); message.textContent = `Saved. Active mode: ${p.mode}.`; message.className = 'form-message success'; }
        catch (error) { message.textContent = error.message || 'Settings could not be saved.'; message.className = 'form-message error'; }
    };
    const themeSelect = document.getElementById('settings-theme');
    themeSelect.value = localStorage.getItem('bugsense-theme') || 'dark'; applyTheme(themeSelect.value);
    themeSelect.onchange = () => { localStorage.setItem('bugsense-theme', themeSelect.value); applyTheme(themeSelect.value); };
    const font = document.getElementById('settings-font-size'); font.value = localStorage.getItem('bugsense-editor-font-size') || '13';
    font.onchange = () => localStorage.setItem('bugsense-editor-font-size', font.value);
    updateActiveNavItem();
}

function applyTheme(theme) { document.documentElement.dataset.theme = theme === 'light' ? 'light' : 'dark'; }

async function renderLearningCentre(targetLessonId = null) {
    const app=document.getElementById('app');
    const categories=[['','All error paths'],['fundamentals','Error Fundamentals'],['traces','Tracebacks & Stack Traces'],['databases','Database Troubleshooting'],['api_http','API & HTTP Debugging'],['django_backend','Django & Backend Errors'],['frontend_js','Frontend & JavaScript Errors'],['deployment','Deployment & Environment'],['verification','Debugging & Verification']];
    app.innerHTML=`${renderSidebar()}<main class="main-content"><div class="content-area learning-hub">
      <header class="learning-hero"><span class="status-badge">BUGSENSE LEARNING LAB</span><h1>Learn to debug with evidence</h1><p>Short, practical lessons built around real errors, logs, root causes, and verification.</p><div class="learning-metrics" id="learning-metrics"><span>Loading your progress…</span></div></header>
      <div class="learning-columns"><section><div class="learning-toolbar"><input id="learning-search" type="search" placeholder="Search errors, logs, technologies…" aria-label="Search debugging lessons"><select id="learning-category" aria-label="Filter by learning path">${categories.map(([value,label])=>`<option value="${value}">${label}</option>`).join('')}</select><select id="learning-difficulty" aria-label="Filter by difficulty"><option value="">All difficulties</option><option>beginner</option><option>intermediate</option><option>advanced</option></select><button class="secondary" id="learning-search-button">Search</button></div>
      <div class="learning-section-heading"><div><h2>Error-based learning paths</h2><p>Choose an error to inspect its evidence and practise the diagnosis.</p></div><span id="learning-result-count"></span></div><div id="learning-topics" class="learning-grid"><div class="loading">Loading lessons…</div></div><div id="learning-lesson"></div></section>
      <aside class="learning-side"><section class="settings-card"><h2>Bookmarked lessons</h2><div id="learning-bookmarks">Loading…</div></section><section class="settings-card"><h2>Recently studied</h2><div id="learning-recent">Loading…</div></section><section class="settings-card"><h2>Your practice activity</h2><div id="learning-activities">Loading…</div></section></aside></div></div></main>`;
    const escape=escapeHTML;
    async function loadLessons(){
      const filters={q:document.getElementById('learning-search').value.trim(),category:document.getElementById('learning-category').value,difficulty:document.getElementById('learning-difficulty').value};
      const host=document.getElementById('learning-topics');host.innerHTML='<div class="loading">Finding matching lessons…</div>';
      try {const list=await window.api.getLearningTopics(filters);document.getElementById('learning-result-count').textContent=`${list.length} lessons`;host.innerHTML=list.length?list.map(topic=>`<article class="learning-card"><div class="learning-card-top"><span class="status-badge">${escape(topic.category.replaceAll('_',' '))}</span><span class="difficulty difficulty-${escape(topic.difficulty)}">${escape(topic.difficulty)}</span></div><h3>${escape(topic.error_name||topic.title)}</h3><p class="learning-topic-title">${escape(topic.title)}</p><p>${escape(topic.description)}</p><div class="learning-card-meta"><span>${escape(topic.technology)}</span>${topic.completed?'<span class="learning-done">✓ Completed</span>':''}</div><div class="learning-card-actions"><button class="primary" data-open-lesson="${topic.id}">Study this error</button><button class="secondary" aria-label="${topic.bookmarked?'Remove bookmark':'Bookmark lesson'}" data-bookmark="${topic.id}">${topic.bookmarked?'★':'☆'}</button></div></article>`).join(''):'<div class="empty-state">No lesson matches these filters. Try another error name or difficulty.</div>';host.querySelectorAll('[data-open-lesson]').forEach(button=>button.addEventListener('click',()=>openLesson(button.dataset.openLesson)));host.querySelectorAll('[data-bookmark]').forEach(button=>button.addEventListener('click',async()=>{button.disabled=true;try{await window.api.updateLearningProgress(button.dataset.bookmark,{bookmarked:button.textContent.trim()==='☆'});await loadLessons();await loadDashboard();}catch(error){button.title=error.message;button.disabled=false;}}));}
      catch(error){host.textContent=error.message||'Debugging lessons are unavailable.';}
    }
    async function loadDashboard(){try{const data=await window.api.getLearningDashboard();const accuracy=data.quiz_accuracy===null?'No quizzes yet':`${data.quiz_accuracy}%`;document.getElementById('learning-metrics').innerHTML=`<div><strong>${data.total_lessons}</strong><span>Debugging lessons</span></div><div><strong>${data.completed_lessons}</strong><span>Completed</span></div><div><strong>${data.challenges_attempted}</strong><span>Challenges attempted</span></div><div><strong>${data.challenges_solved}</strong><span>Solved</span></div><div><strong>${escape(accuracy)}</strong><span>Quiz accuracy</span></div><div><strong>${data.progress_percent}%</strong><span>Learning progress</span></div>`;document.getElementById('learning-bookmarks').innerHTML=data.bookmarked.length?data.bookmarked.map(item=>`<button class="learning-mini-link" data-open-lesson="${item.id}">${escape(item.error_name)} <span>↗</span></button>`).join(''):'<p class="text-secondary">Bookmark a lesson to keep it here.</p>';document.getElementById('learning-recent').innerHTML=data.recently_studied.length?data.recently_studied.map(item=>`<button class="learning-mini-link" data-open-lesson="${item.id}">${escape(item.error_name)} <span>${item.completed?'✓':'Continue'}</span></button>`).join(''):'<p class="text-secondary">Lessons you study will appear here.</p>';document.querySelectorAll('[data-open-lesson]').forEach(button=>button.onclick=()=>openLesson(button.dataset.openLesson));}
      catch(error){document.getElementById('learning-metrics').textContent=error.message||'Progress could not be loaded.';}}
    async function loadActivities(){try{const rows=await window.api.getLearningActivities();const host=document.getElementById('learning-activities');host.innerHTML=rows.slice(0,5).map(item=>`<article class="learning-activity"><span class="status-badge">${escape(item.type)} · ${item.completed?'Complete':'In progress'}</span><p>${escape(item.prompt)}</p><small>${escape(new Date(item.created_at).toLocaleDateString())}</small></article>`).join('')||'<p class="text-secondary">Your submitted answers and quiz attempts appear here.</p>'; }catch(error){document.getElementById('learning-activities').textContent=error.message||'Activity history could not be loaded.';}}
    async function openLesson(id){const panel=document.getElementById('learning-lesson');if(panel.dataset.loadedLesson===String(id))return;panel.innerHTML='<section class="learning-lesson-panel">Loading lesson…</section>';try{const lesson=await window.api.getLearningLesson(id);const hints=lesson.hints||[];panel.innerHTML=`<article class="learning-lesson-panel" id="lesson-${lesson.id}"><div class="lesson-title-row"><div><span class="status-badge">${escape(lesson.category.replaceAll('_',' '))} · ${escape(lesson.difficulty)}</span><h2>${escape(lesson.error_name)}</h2><p>${escape(lesson.technology)}</p></div><button class="secondary" id="lesson-bookmark" aria-pressed="${lesson.bookmarked}">${lesson.bookmarked?'★ Bookmarked':'☆ Bookmark'}</button></div><div class="lesson-grid"><section><h3>What the error means</h3><p>${escape(lesson.description)}</p><h3>Why it occurs</h3><p>${escape(lesson.explanation)}</p><h3>Example log</h3><pre>${escape(lesson.expected_error)}</pre><h3>Line-by-line evidence</h3><ol>${(lesson.line_explanations||[]).map(row=>`<li><code>${escape(row.line)}.</code> ${escape(row.text)}</li>`).join('')}</ol><h3>Root cause</h3><p>${escape(lesson.root_cause)}</p><h3>Reproduce</h3><pre>${escape(lesson.reproduce)}</pre><h3>Troubleshooting</h3><ol>${lesson.troubleshooting.map(step=>`<li>${escape(step)}</li>`).join('')}</ol><h3>Prevention</h3><p>${escape(lesson.prevention)}</p><details class="lesson-correction"><summary>Correction available after your attempt</summary><p>Submit the challenge to reveal the corrected example and explanation.</p></details></section><section class="lesson-challenge"><span class="status-badge">PRACTICE · ${escape(lesson.difficulty)}</span><h3>Debugging challenge</h3><label>Challenge depth<select id="lesson-difficulty"><option value="beginner">Beginner · identify the error</option><option value="intermediate">Intermediate · connect evidence and cause</option><option value="advanced">Advanced · discuss uncertainty and verification</option></select></label><p id="challenge-instruction">${escape(lesson.challenge)}</p><pre>${escape(lesson.expected_error)}\n\n${escape(lesson.buggy_code)}</pre><div id="lesson-hints"></div><button class="secondary" id="lesson-hint-button">Reveal next hint</button><form id="lesson-exercise"><label>Which line or expression is failing?<textarea name="proposed_line" required maxlength="5000" placeholder="Point to the relevant line from the example"></textarea></label><label>What is the likely root cause?<textarea name="root_cause" required maxlength="5000" placeholder="Use evidence from the error"></textarea></label><label>Propose a safe fix<textarea name="proposed_fix" required maxlength="5000" placeholder="Describe your correction"></textarea></label><button class="primary" type="submit">Check my diagnosis</button><p id="lesson-feedback" aria-live="polite"></p><div id="lesson-solution"></div></form><form id="lesson-quiz"><h3>Knowledge check</h3>${lesson.quiz.map((q,i)=>`<fieldset><legend>${escape(q.question)}</legend>${q.options.map((option,j)=>`<label class="quiz-option"><input type="radio" name="quiz-${i}" value="${j}" required> ${escape(option)}</label>`).join('')}</fieldset>`).join('')}<button class="secondary" type="submit">Submit quiz</button><p id="quiz-feedback" aria-live="polite"></p></form></section></div></article>`;panel.dataset.loadedLesson=String(lesson.id);
        let revealed=0;panel.querySelector("#lesson-difficulty").value=lesson.difficulty;panel.querySelector("#lesson-difficulty").onchange=event=>{const guide={beginner:"Identify the failing line and the error meaning.",intermediate:"Connect the error to a likely cause and a safe next check.",advanced:"Separate confirmed evidence from possibilities and describe how you would verify the repair."};panel.querySelector("#challenge-instruction").textContent=guide[event.target.value];};panel.querySelector('#lesson-hint-button').onclick=()=>{if(revealed<hints.length){const p=document.createElement('p');p.className='lesson-hint';p.textContent=`Hint ${revealed+1}: ${hints[revealed++]}`;panel.querySelector('#lesson-hints').append(p);}if(revealed>=hints.length)panel.querySelector('#lesson-hint-button').disabled=true;};
        panel.querySelector('#lesson-bookmark').onclick=async event=>{const button=event.currentTarget;button.disabled=true;try{const updated=await window.api.updateLearningProgress(id,{bookmarked:!lesson.bookmarked});lesson.bookmarked=updated.bookmarked;button.textContent=lesson.bookmarked?'★ Bookmarked':'☆ Bookmark';button.setAttribute('aria-pressed',String(lesson.bookmarked));loadDashboard();}catch(error){button.title=error.message;}finally{button.disabled=false;}};
        panel.querySelector('#lesson-exercise').onsubmit=async event=>{event.preventDefault();const form=event.currentTarget;const button=form.querySelector('button[type=submit]');button.disabled=true;const result=panel.querySelector('#lesson-feedback');result.textContent='Checking your diagnosis…';const values=Object.fromEntries(new FormData(form));try{const answer=await window.api.submitLearningExercise(id,{...values,difficulty:panel.querySelector("#lesson-difficulty").value,hints_revealed:revealed});result.textContent=answer.solved?'Correct: '+answer.feedback:answer.feedback;result.className=answer.solved?'success':'error';panel.querySelector('#lesson-solution').innerHTML=`<h4>Evidence-based explanation</h4><p>${escape(answer.root_cause)}</p><h4>Corrected example</h4><pre>${escape(answer.corrected_code)}</pre><p>${escape(answer.correction_explanation)}</p>`;if(answer.solved){loadDashboard();loadActivities();}}catch(error){result.textContent=error.message||'Your answer could not be checked.';}finally{button.disabled=false;}};
        panel.querySelector('#lesson-quiz').onsubmit=async event=>{event.preventDefault();const answers=lesson.quiz.map((_,i)=>Number(new FormData(event.currentTarget).get(`quiz-${i}`)));const feedback=panel.querySelector('#quiz-feedback');try{const score=await window.api.submitLearningQuiz(id,answers);feedback.innerHTML=`Score: ${score.score}/${score.total}<ul>${score.explanations.map(item=>`<li>${escape(item.explanation)}</li>`).join('')}</ul>`;if(score.score>0){await window.api.updateLearningProgress(id,{completed:true});loadDashboard();loadLessons();loadActivities();}}catch(error){feedback.textContent=error.message||'Quiz result could not be saved.';}};
        panel.scrollIntoView({behavior:'smooth',block:'start'});
      }catch(error){panel.textContent=error.message||'This lesson could not be loaded.';}}
    document.getElementById('learning-search-button').onclick=loadLessons;document.getElementById('learning-search').onkeydown=event=>{if(event.key==='Enter')loadLessons();};document.getElementById('learning-category').onchange=loadLessons;document.getElementById('learning-difficulty').onchange=loadLessons;
    await Promise.all([loadLessons(),loadDashboard(),loadActivities()]);
    if(targetLessonId)openLesson(targetLessonId);else if(window.learningRecommendedLessonId){const id=window.learningRecommendedLessonId;window.learningRecommendedLessonId=null;openLesson(id);}
    updateActiveNavItem();
}

async function renderProfile() {
    const app = document.getElementById('app');
    app.innerHTML = `${renderSidebar()}<main class="main-content"><div class="content-area"><header class="page-heading"><h1>Your profile</h1><p>Update the name and email associated with your account.</p></header><div id="profile-card" class="profile-card">Loading account…</div></div></main>`;
    try {
        const profile = await window.api.getProfile();
        const host = document.getElementById('profile-card');
        if (host) host.innerHTML = `<h2>Account details</h2><form id="profile-form" class="settings-fields"><label>Display name<input name="first_name" maxlength="150" value="${escapeHTML(profile.first_name || '')}"></label><label>Last name<input name="last_name" maxlength="150" value="${escapeHTML(profile.last_name || '')}"></label><label>Email<input name="email" type="email" required value="${escapeHTML(profile.email || '')}"></label><label>Username<input value="${escapeHTML(profile.username)}" disabled></label><small>Member since ${escapeHTML(profile.date_joined ? new Date(profile.date_joined).toLocaleDateString() : 'Unknown')}</small><div><button class="primary" type="submit">Save profile</button><p id="profile-message" role="status" aria-live="polite"></p></div></form><section class="account-security"><h3>Account security</h3><p>Password changes are not available in the current backend.</p></section>`;
        document.getElementById('profile-form').addEventListener('submit', async event => { event.preventDefault(); const form = event.currentTarget; const msg = document.getElementById('profile-message'); const button = form.querySelector('button[type="submit"]'); button.disabled = true; try { await window.api.updateProfile({ first_name: form.elements.first_name.value.trim(), last_name: form.elements.last_name.value.trim(), email: form.elements.email.value.trim() }); msg.textContent = 'Profile saved.'; msg.className = 'form-message success'; } catch (error) { msg.textContent = error.message || 'Profile could not be saved.'; msg.className = 'form-message error'; } finally { button.disabled = false; } });
    } catch {
        const host = document.getElementById('profile-card');
        if (host) host.textContent = 'Profile details are temporarily unavailable.';
    }
    updateActiveNavItem();
}

function toggleAIPanel() {
    document.querySelector('.workspace-layout')?.classList.toggle('ai-panel-collapsed');
}

// Terminal Tab Switching
function switchTerminalTab(tab) {
    activeTerminalTab = tab;
    document.querySelectorAll('.terminal-tab').forEach(t => t.classList.remove('active'));
    const selected = document.querySelector(`.terminal-tab[data-tab="${tab}"]`);
    selected?.classList.add('active');
    
    const terminalOutput = document.getElementById('terminal-output');
    const tabContents = {
        output: 'No output yet. Click "Run Code" to execute.',
        errors: 'No errors yet.',
        explain: 'Run code and choose Explain Output, or open LogSense to explain a saved technical log.',
        analysis: analysisResult ? JSON.stringify(analysisResult, null, 2) : 'No analysis yet. Click "Analyze" to get AI diagnosis.',
        diff: window.pendingRepair ? window.pendingRepair.diff : 'No repair diff available.',
        verification: 'No verification results yet. Click "Verify" to test your code.'
    };
    
    terminalOutput.textContent = tabContents[tab] || 'No content.';
}

// Load Example
function loadExample() {
    const exampleCode = `def calculate_total(price, quantity):
    return price * quantity

print(total_price)`;

    setEditorCode(exampleCode);
}

// Clear Error
function clearError() {
    const terminalOutput = document.getElementById('terminal-output');
    terminalOutput.textContent = 'Error cleared.';
}

// Clear Logs
function clearLogs() {
    const terminalOutput = document.getElementById('terminal-output');
    terminalOutput.textContent = 'Logs cleared.';
}

// Run Code
async function runCode() {
    const code = getEditorCode();
    const language = document.getElementById('language').value;
    const terminalOutput = document.getElementById('terminal-output');
    const runBtn = document.getElementById('run-code-btn');

    if (!code.trim()) {
        terminalOutput.textContent = 'Error: No source code to execute. Please enter code first.';
        return;
    }

    runBtn.disabled = true;
    runBtn.innerHTML = '<div class="loading-spinner"></div> Running...';
    terminalOutput.textContent = 'Executing code...';

    try {
        const result = await window.api.executeCode({
            source_code: code,
            language: language,
            session_id: currentSessionId,
        });
        setCurrentSessionId(result.session_id || currentSessionId);

        let output = `=== Execution Result ===\n`;
        output += `Exit Code: ${result.exit_code}\n`;
        output += `Duration: ${result.duration_ms}ms\n\n`;

        if (result.exit_code === 0) {
            output += `Status: SUCCESS\n`;
            if (result.stdout) {
                output += `\n=== Output ===\n${result.stdout}`;
            }
        } else {
            output += `Status: FAILED\n`;
            if (result.stderr) {
                output += `\n=== Error Output ===\n${result.stderr}`;
            }
        }

        if (result.timed_out) {
            output += `\nWarning: Execution timed out`;
        }

        terminalOutput.textContent = output;
        window.bugSenseLastOutputLog = [result.stdout, result.stderr].filter(Boolean).join('\n');
        const explainButton = document.getElementById('explain-output-btn');
        if (explainButton) explainButton.disabled = !window.bugSenseLastOutputLog.trim();
        
        // Store error for analysis
        window.bugSenseLastTraceback = result.exit_code !== 0 ? result.stderr || '' : '';
    } catch (error) {
        if (error.sessionId) setCurrentSessionId(error.sessionId);
        terminalOutput.textContent = 'Error: ' + error.message;
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Run Code
        `;
    }
}

// Analyze Code
async function analyzeCode() {
    const code = getEditorCode();
    const terminalOutput = document.getElementById('terminal-output');
    const analyzeBtn = document.getElementById('analyze-btn');
    const aiDiagnosisContent = document.getElementById('ai-diagnosis-content');

    if (!code.trim()) {
        terminalOutput.textContent = 'Enter or load source code before analyzing.';
        return;
    }

    analyzeBtn.disabled = true;
    aiDiagnosisContent.innerHTML = '<div class="loading"><div class="loading-spinner"></div> Analyzing...</div>';

    try {
        // First, try to run the code to get actual error
        let actualError = '';
        let trace = '';
        try {
            const execResult = await window.api.executeCode({
                source_code: code,
                language: 'python',
                session_id: currentSessionId,
            });
            setCurrentSessionId(execResult.session_id || currentSessionId);
            if (execResult.exit_code !== 0 && execResult.stderr) {
                actualError = execResult.stderr;
                trace = execResult.stderr;
            }
        } catch (e) {
            if (e.sessionId) setCurrentSessionId(e.sessionId);
            actualError = 'Execution failed';
        }

        const result = await window.api.analyzeCode({
            source_code: code,
            error_message: actualError || 'No error message',
            terminal_logs: trace,
            language: 'python',
            session_id: currentSessionId,
            allow_external_ai: document.getElementById('ai-share-consent')?.checked === true,
        });

        analysisResult = result;
        setCurrentSessionId(result.session_id || currentSessionId);
        const aiResult = result.ai_analysis || {};
        const staticResult = result.static_analysis || {};
        const runtimeDiagnosis = result.runtime_diagnosis || {};
        
        aiDiagnosisContent.innerHTML = `
            <div class="diagnosis-item"><div class="diagnosis-label">AI Provider</div><div class="diagnosis-value ai">${escapeHTML(aiResult.provider || 'Gemini')}${aiResult.model ? ` (${escapeHTML(aiResult.model)})` : ''}</div></div>
            ${aiResult.error || aiResult.status === 'consent_required' ? `<div class="diagnosis-item"><div class="diagnosis-label">AI Analysis Status</div><div class="diagnosis-value ${aiResult.error ? 'text-error' : ''}">${escapeHTML(aiResult.error || aiResult.message || aiResult.status)}${aiResult.error_type ? ` · ${escapeHTML(aiResult.error_type)}` : ''}</div></div>` : ''}
            <div class="diagnosis-item">
                <div class="diagnosis-label">Error Type</div>
                <div class="diagnosis-value">${escapeHTML(aiResult.error_category || runtimeDiagnosis.error_category || 'Static analysis')}</div>
            </div>
            <div class="diagnosis-item">
                <div class="diagnosis-label">Summary</div>
                <div class="diagnosis-value">${escapeHTML(aiResult.summary || runtimeDiagnosis.summary || 'Review the static findings below, then enable Gemini processing for an AI diagnosis.')}</div>
            </div>
            ${staticResult.syntax_errors?.length ? `<div class="diagnosis-item"><div class="diagnosis-label">Syntax errors</div><div class="diagnosis-value text-error">${escapeHTML(staticResult.syntax_errors.map(item => `Line ${item.line}: ${item.message}`).join('\n'))}</div></div>` : ''}
            ${staticResult.undefined_names?.length ? `<div class="diagnosis-item"><div class="diagnosis-label">Possibly undefined names</div><div class="diagnosis-value text-warning">${escapeHTML(staticResult.undefined_names.map(item => item.name || item).join(', '))}</div></div>` : ''}
            ${aiResult.possible_causes ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Possible Causes</div>
                <div class="diagnosis-value ai">${escapeHTML(Array.isArray(aiResult.possible_causes) ? aiResult.possible_causes.join(', ') : aiResult.possible_causes)}</div>
            </div>
            ` : ''}
            <div class="diagnosis-item">
                <div class="diagnosis-label">Confidence</div>
                <div class="diagnosis-value">${Number.isFinite(aiResult.confidence) ? `${aiResult.confidence}%` : 'Not provided'}</div>
            </div>
            ${aiResult.undefined_variable ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Undefined Variable</div>
                <div class="diagnosis-value text-error">${escapeHTML(aiResult.undefined_variable)}</div>
            </div>
            ` : ''}
            ${aiResult.available_functions ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Available Functions</div>
                <div class="diagnosis-value">${escapeHTML(aiResult.available_functions.join(', '))}</div>
            </div>
            ` : ''}
        `;

        terminalOutput.textContent = `Analysis ${result.analysis_status || 'complete'}. Static findings are shown with the AI provider status.`;
    } catch (error) {
        aiDiagnosisContent.innerHTML = `<div class="diagnosis-value text-error">Analysis failed: ${error.message}</div>`;
        terminalOutput.textContent = 'Error: ' + error.message;
    } finally {
        analyzeBtn.disabled = false;
    }
}

// Repair Code
async function repairCode() {
    const code = getEditorCode();
    const terminalOutput = document.getElementById('terminal-output');
    const repairBtn = document.getElementById('repair-btn');
    const aiDiagnosisContent = document.getElementById('ai-diagnosis-content');

    if (!code.trim()) {
        terminalOutput.textContent = 'Error: No source code to repair.';
        return;
    }

    repairBtn.disabled = true;
    aiDiagnosisContent.innerHTML = '<div class="loading"><div class="loading-spinner"></div> Generating repair...</div>';

    try {
        // First, run the code to get the actual error
        let actualError = '';
        let exitCode = 0;
        
        try {
            const execResult = await window.api.executeCode({
                source_code: code,
                language: 'python',
                session_id: currentSessionId,
            });
            setCurrentSessionId(execResult.session_id || currentSessionId);
            exitCode = execResult.exit_code;
            
            // Update terminal with execution result
            let output = `=== Execution Result ===\n`;
            output += `Exit Code: ${execResult.exit_code}\n\n`;
            
            if (execResult.exit_code === 0) {
                output += `Status: SUCCESS\n`;
                if (execResult.stdout) {
                    output += `\n=== Output ===\n${execResult.stdout}`;
                }
                terminalOutput.textContent = output;
                aiDiagnosisContent.innerHTML = '<div class="diagnosis-value text-secondary">No error detected. Code executes successfully.</div>';
                repairBtn.disabled = false;
                return;
            } else {
                output += `Status: FAILED\n`;
                if (execResult.stderr) {
                    output += `\n=== Error Output ===\n${execResult.stderr}`;
                    actualError = execResult.stderr;
                }
                terminalOutput.textContent = output;
            }
        } catch (e) {
            if (e.sessionId) setCurrentSessionId(e.sessionId);
            actualError = 'Execution failed: ' + e.message;
            terminalOutput.textContent = actualError;
        }

        // If no error after execution, show message and return
        if (!actualError && exitCode === 0) {
            aiDiagnosisContent.innerHTML = '<div class="diagnosis-value text-secondary">No error detected. Code executes successfully.</div>';
            repairBtn.disabled = false;
            return;
        }

        const result = await window.api.generateRepair({
            source_code: code,
            error_message: actualError || 'No error message',
            traceback: actualError,
            diagnosis: analysisResult?.ai_analysis || {},
            language: 'python',
            session_id: currentSessionId,
            allow_external_ai: document.getElementById('ai-share-consent')?.checked === true,
        });
        if (result.error) {
            aiDiagnosisContent.innerHTML = `
                <div class="diagnosis-item">
                    <div class="diagnosis-label">Error</div>
                    <div class="diagnosis-value text-error">${escapeHTML(result.error)}</div>
                </div>
                <div class="diagnosis-item">
                    <div class="diagnosis-label">Suggestion</div>
                    <div class="diagnosis-value text-secondary">AI provider failed. Try heuristic repair as a fallback.</div>
                </div>
                <div style="margin-top: 16px;">
                    <button class="secondary" onclick="repairWithHeuristic()" style="width: 100%;">Try Heuristic Repair</button>
                </div>
            `;
            terminalOutput.textContent = 'Error: ' + result.error;
            return;
        }

        // Validate the repair
        if (!result.repaired_code || result.repaired_code === code) {
            aiDiagnosisContent.innerHTML = `
                <div class="diagnosis-item">
                    <div class="diagnosis-label">Error</div>
                    <div class="diagnosis-value text-error">Repair did not generate valid code</div>
                </div>
            `;
            terminalOutput.textContent = 'Error: Repair did not generate valid code';
            return;
        }

        window.pendingRepair = { ...result, original_code: code };
        currentAttemptId = result.attempt_id;

        aiDiagnosisContent.innerHTML = `
            <div class="diagnosis-item"><div class="diagnosis-label">Provider</div><div class="diagnosis-value ai">${escapeHTML(result.provider || 'Unknown')}${result.model ? ` (${escapeHTML(result.model)})` : ''}</div></div>
            <div class="diagnosis-item">
                <div class="diagnosis-label">Repair Source</div>
                <div class="diagnosis-value ai">${escapeHTML(result.source === 'ai_gemini' ? 'AI generated by Gemini' : result.source === 'ai_openai' ? 'AI generated by OpenAI' : (result.source || 'Unknown'))}</div>
            </div>
            ${result.warning ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Note</div>
                <div class="diagnosis-value text-warning">${escapeHTML(result.warning)}</div>
            </div>
            ` : ''}
            <div class="diagnosis-item">
                <div class="diagnosis-label">Diff</div>
                <div class="diagnosis-value" style="font-family: 'JetBrains Mono', monospace; font-size: 11px; white-space: pre-wrap; max-height: 200px; overflow-y: auto;">${escapeHTML(result.diff || 'No diff available')}</div>
            </div>
            <div style="margin-top: 16px; display: flex; gap: 8px;">
                <button class="success" onclick="applyRepair()" style="flex: 1;">Apply Repair</button>
                <button class="danger" onclick="rejectRepair()" style="flex: 1;">Reject</button>
            </div>
        `;

        terminalOutput.textContent = 'Repair generated. Review the AI Diagnosis panel and choose to Apply or Reject.';
    } catch (error) {
        console.error('Repair error:', error);
        aiDiagnosisContent.innerHTML = `<div class="diagnosis-value text-error">Repair failed: ${error.message}</div>`;
        terminalOutput.textContent = 'Error: ' + error.message;
    } finally {
        repairBtn.disabled = false;
    }
}

// Repair with Heuristic (Quick Fix)
async function repairWithHeuristic() {
    const code = getEditorCode();
    const terminalOutput = document.getElementById('terminal-output');
    const aiDiagnosisContent = document.getElementById('ai-diagnosis-content');
    const heuristicBtn = document.getElementById('heuristic-repair-btn');

    if (!code.trim()) {
        terminalOutput.textContent = 'Error: No source code to repair.';
        return;
    }

    // First run the code to get the actual error if not already present
    if (!terminalOutput.textContent.includes('Error Output') && !terminalOutput.textContent.includes('FAILED')) {
        heuristicBtn.disabled = true;
        aiDiagnosisContent.innerHTML = '<div class="loading"><div class="loading-spinner"></div> Running code to detect error...</div>';
        
        try {
            const execResult = await window.api.executeCode({
                source_code: code,
                language: 'python',
                session_id: currentSessionId,
            });
            setCurrentSessionId(execResult.session_id || currentSessionId);
            
            let output = `=== Execution Result ===\n`;
            output += `Exit Code: ${execResult.exit_code}\n\n`;
            
            if (execResult.exit_code === 0) {
                output += `Status: SUCCESS\n`;
                if (execResult.stdout) {
                    output += `\n=== Output ===\n${execResult.stdout}`;
                }
                terminalOutput.textContent = output;
                aiDiagnosisContent.innerHTML = '<div class="diagnosis-value text-secondary">No error detected. Code executes successfully.</div>';
                heuristicBtn.disabled = false;
                return;
            } else {
                output += `Status: FAILED\n`;
                if (execResult.stderr) {
                    output += `\n=== Error Output ===\n${execResult.stderr}`;
                }
                terminalOutput.textContent = output;
            }
        } catch (execError) {
            if (execError.sessionId) setCurrentSessionId(execError.sessionId);
            terminalOutput.textContent = 'Error: Failed to execute code: ' + execError.message;
            aiDiagnosisContent.innerHTML = '<div class="diagnosis-value text-error">Failed to execute code</div>';
            heuristicBtn.disabled = false;
            return;
        }
    }

    heuristicBtn.disabled = true;
    aiDiagnosisContent.innerHTML = '<div class="loading"><div class="loading-spinner"></div> Generating quick fix...</div>';

    try {
        // Get actual error from terminal if available
        let actualError = terminalOutput.textContent;
        if (actualError.includes('Error Output')) {
            const errorMatch = actualError.match(/=== Error Output ===\n([\s\S]+)/);
            if (errorMatch) {
                actualError = errorMatch[1].trim();
            }
        }

        const result = await window.api.repairWithHeuristic({
            source_code: code,
            error_message: actualError || 'No error message',
            language: 'python',
        });

        window.pendingRepair = result;
        currentAttemptId = result.attempt_id;

        if (result.error) {
            aiDiagnosisContent.innerHTML = `<div class="diagnosis-value text-error">Quick fix failed: ${result.error}</div>`;
            terminalOutput.textContent = 'Error: ' + result.error;
            return;
        }

        aiDiagnosisContent.innerHTML = `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Repair Source</div>
                <div class="diagnosis-value ai">${result.source || 'Heuristic'}</div>
            </div>
            ${result.warning ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Note</div>
                <div class="diagnosis-value text-warning">${result.warning}</div>
            </div>
            ` : ''}
            <div class="diagnosis-item">
                <div class="diagnosis-label">Diff</div>
                <div class="diagnosis-value" style="font-family: 'JetBrains Mono', monospace; font-size: 11px; white-space: pre-wrap; max-height: 200px; overflow-y: auto;">${result.diff || 'No diff available'}</div>
            </div>
            <div style="margin-top: 16px; display: flex; gap: 8px;">
                <button class="success" onclick="applyRepair()" style="flex: 1;">Apply Fix</button>
                <button class="danger" onclick="rejectRepair()" style="flex: 1;">Reject</button>
            </div>
        `;

        terminalOutput.textContent = 'Quick fix generated. Review and choose to Apply or Reject.';
    } catch (error) {
        console.error('Quick fix error:', error);
        aiDiagnosisContent.innerHTML = `<div class="diagnosis-value text-error">Quick fix failed: ${error.message}</div>`;
        terminalOutput.textContent = 'Error: ' + error.message;
    } finally {
        heuristicBtn.disabled = false;
    }
}

// Apply Repair
function applyRepair() {
    if (window.pendingRepair && window.pendingRepair.repaired_code) {
        window.lastAppliedRepair = { ...window.pendingRepair };
        setEditorCode(window.pendingRepair.repaired_code);
        
        const terminalOutput = document.getElementById('terminal-output');
        terminalOutput.textContent = 'Repair applied. Click "Run Code" to verify the fix.';
        
        window.pendingRepair = null;
        
        // Reset AI panel
        const aiDiagnosisContent = document.getElementById('ai-diagnosis-content');
        aiDiagnosisContent.innerHTML = `
            <div class="empty-content">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p style="font-size: 13px;">Repair applied successfully</p>
            </div>
        `;
    }
}

// Reject Repair
function rejectRepair() {
    window.pendingRepair = null;

    const terminalOutput = document.getElementById('terminal-output');
    terminalOutput.textContent = 'Repair rejected. Original code preserved.';

    const aiDiagnosisContent = document.getElementById('ai-diagnosis-content');
    aiDiagnosisContent.innerHTML = `
        <div class="empty-content">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <p style="font-size: 13px;">Repair rejected</p>
        </div>
    `;
}

// Verify Code
async function verifyCode() {
    const code = getEditorCode();
    const language = document.getElementById('language').value;
    const terminalOutput = document.getElementById('terminal-output');
    const verifyBtn = document.getElementById('verify-btn');

    if (!code.trim()) {
        terminalOutput.textContent = 'Error: No source code to verify. Please enter code first.';
        return;
    }

    verifyBtn.disabled = true;
    verifyBtn.innerHTML = '<div class="loading-spinner"></div> Verifying...';
    terminalOutput.textContent = 'Running verification checks...';

    try {
        const applied = window.lastAppliedRepair;
        const result = await window.api.verifyRepair({
            original_code: applied?.original_code || '', repaired_code: code, language,
            session_id: currentSessionId, attempt_id: applied?.attempt_id,
        });
        let output = `=== Verification Result ===\nStatus: ${(result.status || 'blocked').toUpperCase()}\nSyntax: ${result.syntax_check}\nExecution: ${result.execution_check}\n`;
        if (result.execution_result?.stdout) output += `\n=== Output ===\n${result.execution_result.stdout}`;
        if (result.execution_result?.stderr) output += `\n=== Details ===\n${result.execution_result.stderr}`;
        if (result.status === 'blocked') output += '\nExecution was unavailable, so this candidate was not marked as passed.';
        terminalOutput.textContent = output;
    } catch (error) {
        terminalOutput.textContent = 'Error: ' + error.message;
    } finally {
        verifyBtn.disabled = false;
        verifyBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Verify
        `;
    }
}

// Open Session
async function openSession(sessionId) {
    try {
        const session = await window.api.getSession(sessionId);
        setCurrentSessionId(session.id);
        if (session.language === 'technical-log' && session.terminal_logs) {
            window.logSenseSessionId = session.id;
            window.logSensePrefill = session.terminal_logs;
            window.location.hash = '#/logsense';
            return;
        }
        setEditorCode(session.source_code || '');
        analysisResult = null;
        window.location.hash = '#/workspace';
    } catch (error) {
        document.getElementById('terminal-output')?.replaceChildren(document.createTextNode('Failed to load session: ' + error.message));
    }
}

// Initialize
window.addEventListener('load', () => {
    handleRoute();
});

window.addEventListener('hashchange', () => {
    handleRoute();
});

window.addEventListener('keydown', (event) => {
    if (!window.location.hash.startsWith('#/workspace') || !(event.ctrlKey || event.metaKey)) return;
    if (event.key === 'Enter') { event.preventDefault(); runCode(); }
    if (event.shiftKey && event.key.toLowerCase() === 'a') { event.preventDefault(); analyzeCode(); }
    if (event.shiftKey && event.key.toLowerCase() === 'r') { event.preventDefault(); repairCode(); }
    if (event.shiftKey && event.key.toLowerCase() === 'v') { event.preventDefault(); verifyCode(); }
});

if (typeof localStorage !== 'undefined') applyTheme(localStorage.getItem('bugsense-theme') || 'dark');
