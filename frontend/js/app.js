// BugSense AI - Premium Debugging Studio
let currentSessionId = null;
let currentAttemptId = null;
let analysisResult = null;
window.monacoEditor = null;
window.pendingRepair = null;
let monacoLoaded = false;
let sidebarOpen = false;
let activeTerminalTab = 'output';

// Monaco Editor Loader
function loadMonacoEditor() {
    if (monacoLoaded || window.monacoEditor) {
        if (window.monacoEditor) {
            window.monacoEditor.layout();
        }
        return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js';
    script.onload = () => {
        require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
        require(['vs/editor/editor.main'], function () {
            monacoLoaded = true;
            initializeMonaco();
        });
    };
    document.head.appendChild(script);
}

function initializeMonaco() {
    const container = document.getElementById('monaco-editor-container');
    if (container && !window.monacoEditor) {
        // Ensure container has dimensions
        container.style.height = '400px';
        container.style.width = '100%';
        
        window.monacoEditor = monaco.editor.create(container, {
            value: '# Enter your Python code here\ndef calculate_total(price, quantity):\n    return price * quantity\n\nprint(total_price)',
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            lineNumbers: 'on',
            fontSize: 13,
            fontFamily: 'JetBrains Mono',
            padding: { top: 16 },
        });
        
        // Force layout after a short delay
        setTimeout(() => {
            if (window.monacoEditor) {
                window.monacoEditor.layout();
            }
        }, 100);
    } else if (container && window.monacoEditor) {
        window.monacoEditor.layout();
    }
}

// Router
function handleRoute() {
    const hash = window.location.hash || '#/dashboard';
    const app = document.getElementById('app');

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
        case '#/history':
            renderHistory();
            break;
        case '#/settings':
            renderSettings();
            break;
        default:
            renderDashboard();
    }
    
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

// Toggle Sidebar
function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open', sidebarOpen);
    }
}

// Render Sidebar
function renderSidebar() {
    return `
        <div class="sidebar" id="sidebar">
            <div class="sidebar-brand" onclick="window.location.hash='#/dashboard'">
                🐛
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
                <a href="#/settings" class="nav-item" id="nav-settings">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 00-1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572-1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 001.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span>Settings</span>
                </a>
            </nav>
            <div class="sidebar-footer">
                <a href="#" onclick="window.auth.logout()" class="nav-item">
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

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            await window.api.login(username, password);
            window.location.hash = '#/dashboard';
        } catch (error) {
            alert('Login failed: ' + error.message);
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

        try {
            await window.api.register(username, email, password);
            window.location.hash = '#/dashboard';
        } catch (error) {
            alert('Registration failed: ' + error.message);
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
                </div>
            </div>
        `;
        
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
    document.getElementById('app').innerHTML = `
        ${renderSidebar()}
        <div class="main-content">
            <div class="workspace-header">
                <div class="workspace-title">Debugging Workspace</div>
                <div class="workspace-controls">
                    <select id="language" style="width: auto;">
                        <option value="python">Python</option>
                    </select>
                </div>
            </div>
            <div class="content-area" style="padding: 16px;">
                <div class="workspace-layout">
                    <div class="editor-section">
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
                                <button class="terminal-tab active" onclick="switchTerminalTab('output')">Output</button>
                                <button class="terminal-tab" onclick="switchTerminalTab('errors')">Errors</button>
                                <button class="terminal-tab" onclick="switchTerminalTab('analysis')">AI Analysis</button>
                                <button class="terminal-tab" onclick="switchTerminalTab('diff')">Repair Diff</button>
                                <button class="terminal-tab" onclick="switchTerminalTab('verification')">Verification</button>
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

    setTimeout(() => {
        loadMonacoEditor();
        // Fallback: try again if Monaco didn't load
        setTimeout(() => {
            if (!window.monacoEditor) {
                loadMonacoEditor();
            }
        }, 500);
    }, 100);
    
    updateActiveNavItem();
}

// Render History
async function renderHistory() {
    try {
        const history = await window.api.getHistory();
        document.getElementById('app').innerHTML = `
            ${renderSidebar()}
            <div class="main-content">
                <div class="workspace-header">
                    <div class="workspace-title">Session History</div>
                </div>
                <div class="content-area">
                    <div class="sessions-list" id="history-list">
                        ${history.length === 0 ? `
                            <div class="empty-state">
                                <div class="empty-state-icon">📂</div>
                                <p>No debugging sessions yet.</p>
                                <button class="secondary" onclick="window.location.hash='#/workspace'" style="margin-top: 12px;">Start New Session</button>
                            </div>
                        ` : history.map(session => `
                            <div class="session-row">
                                <div class="session-info">
                                    <div class="session-name">Session #${session.id}</div>
                                    <div class="session-meta">
                                        <span>${session.language || 'Python'}</span>
                                        <span>${new Date(session.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                                <span class="session-status ${session.status || 'pending'}">${session.status || 'Pending'}</span>
                                <div class="session-action">
                                    <button class="secondary" onclick="openSession(${session.id})">Open</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        
        updateActiveNavItem();
    } catch (error) {
        console.error('Failed to load history:', error);
        document.getElementById('app').innerHTML = `
            ${renderSidebar()}
            <div class="main-content">
                <div class="content-area">
                    <div class="empty-content">
                        <p>Failed to load history. Please try again.</p>
                    </div>
                </div>
            </div>
        `;
    }
}

// Render Settings
function renderSettings() {
    document.getElementById('app').innerHTML = `
        ${renderSidebar()}
        <div class="main-content">
            <div class="workspace-header">
                <div class="workspace-title">Settings</div>
            </div>
            <div class="content-area">
                <div class="empty-content">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 00-1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572-1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 001.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <p>Settings panel coming soon.</p>
                </div>
            </div>
        </div>
    `;
    
    updateActiveNavItem();
}

// Terminal Tab Switching
function switchTerminalTab(tab) {
    activeTerminalTab = tab;
    document.querySelectorAll('.terminal-tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    
    const terminalOutput = document.getElementById('terminal-output');
    const tabContents = {
        output: 'No output yet. Click "Run Code" to execute.',
        errors: 'No errors yet.',
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

    if (window.monacoEditor) {
        window.monacoEditor.setValue(exampleCode);
    }
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
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
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
        
        // Store error for analysis
        if (result.exit_code !== 0 && result.stderr) {
            currentSessionId = result.session_id;
        }
    } catch (error) {
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
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
    const terminalOutput = document.getElementById('terminal-output');
    const analyzeBtn = document.getElementById('analyze-btn');
    const aiDiagnosisContent = document.getElementById('ai-diagnosis-content');

    if (!code.trim()) {
        terminalOutput.textContent = 'Error: No source code to analyze.';
        return;
    }

    analyzeBtn.disabled = true;
    aiDiagnosisContent.innerHTML = '<div class="loading"><div class="loading-spinner"></div> Analyzing...</div>';

    try {
        // First, try to run the code to get actual error
        let actualError = '';
        try {
            const execResult = await window.api.executeCode({
                source_code: code,
                language: 'python',
            });
            if (execResult.exit_code !== 0 && execResult.stderr) {
                actualError = execResult.stderr;
            }
        } catch (e) {
            actualError = 'Execution failed';
        }

        const result = await window.api.analyzeCode({
            source_code: code,
            error_message: actualError || 'No error message',
            language: 'python',
        });

        analysisResult = result;
        
        aiDiagnosisContent.innerHTML = `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Error Type</div>
                <div class="diagnosis-value">${result.error_category || 'Unknown'}</div>
            </div>
            <div class="diagnosis-item">
                <div class="diagnosis-label">Summary</div>
                <div class="diagnosis-value">${result.summary || 'No summary available'}</div>
            </div>
            ${result.possible_causes ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Possible Causes</div>
                <div class="diagnosis-value ai">${Array.isArray(result.possible_causes) ? result.possible_causes.join(', ') : result.possible_causes}</div>
            </div>
            ` : ''}
            <div class="diagnosis-item">
                <div class="diagnosis-label">Confidence</div>
                <div class="diagnosis-value">${result.confidence || 0}%</div>
            </div>
            ${result.undefined_variable ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Undefined Variable</div>
                <div class="diagnosis-value text-error">${result.undefined_variable}</div>
            </div>
            ` : ''}
            ${result.available_functions ? `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Available Functions</div>
                <div class="diagnosis-value">${result.available_functions.join(', ')}</div>
            </div>
            ` : ''}
        `;

        terminalOutput.textContent = 'Analysis complete. Check the AI Diagnosis panel for details.';
    } catch (error) {
        aiDiagnosisContent.innerHTML = `<div class="diagnosis-value text-error">Analysis failed: ${error.message}</div>`;
        terminalOutput.textContent = 'Error: ' + error.message;
    } finally {
        analyzeBtn.disabled = false;
    }
}

// Repair Code
async function repairCode() {
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
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
            });
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
            actualError = 'Execution failed: ' + e.message;
            terminalOutput.textContent = actualError;
        }

        // If no error after execution, show message and return
        if (!actualError && exitCode === 0) {
            aiDiagnosisContent.innerHTML = '<div class="diagnosis-value text-secondary">No error detected. Code executes successfully.</div>';
            repairBtn.disabled = false;
            return;
        }

        console.log('Sending repair request with error:', actualError);
        const result = await window.api.generateRepair({
            source_code: code,
            error_message: actualError || 'No error message',
            language: 'python',
        });
        console.log('Repair response:', result);

        window.pendingRepair = result;
        currentAttemptId = result.attempt_id;

        if (result.error) {
            aiDiagnosisContent.innerHTML = `
                <div class="diagnosis-item">
                    <div class="diagnosis-label">Error</div>
                    <div class="diagnosis-value text-error">${result.error}</div>
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

        aiDiagnosisContent.innerHTML = `
            <div class="diagnosis-item">
                <div class="diagnosis-label">Repair Source</div>
                <div class="diagnosis-value ai">${result.source || 'Unknown'}</div>
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
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
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
            });
            
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
        if (window.monacoEditor) {
            window.monacoEditor.setValue(window.pendingRepair.repaired_code);
        }
        
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
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
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
        const result = await window.api.executeCode({
            source_code: code,
            language: language,
            session_id: currentSessionId,
        });

        let output = `=== Verification Result ===\n`;
        output += `Exit Code: ${result.exit_code}\n`;
        output += `Duration: ${result.duration_ms}ms\n\n`;

        if (result.exit_code === 0) {
            output += `Status: VERIFIED\n`;
            output += `Code executed successfully\n`;
            if (result.stdout) {
                output += `\n=== Output ===\n${result.stdout}`;
            }
        } else {
            output += `Status: FAILED\n`;
            output += `Code execution failed\n`;
            if (result.stderr) {
                output += `\n=== Error Output ===\n${result.stderr}`;
            }
        }

        if (result.timed_out) {
            output += `\nWarning: Execution timed out`;
        }

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
        currentSessionId = session.id;
        
        window.location.hash = '#/workspace';
        
        setTimeout(() => {
            if (window.monacoEditor && session.source_code) {
                window.monacoEditor.setValue(session.source_code);
            }
        }, 200);
    } catch (error) {
        alert('Failed to load session: ' + error.message);
    }
}

// Initialize
window.addEventListener('load', () => {
    handleRoute();
});

window.addEventListener('hashchange', () => {
    handleRoute();
});
