// BugSense AI - Main Application
let currentSessionId = null;
let currentAttemptId = null;
let analysisResult = null;
window.monacoEditor = null;
window.pendingRepair = null;

// Monaco Editor Loader
function loadMonacoEditor() {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js';
    script.onload = () => {
        require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
        require(['vs/editor/editor.main'], function () {
            initializeMonaco();
        });
    };
    document.head.appendChild(script);
}

function initializeMonaco() {
    const container = document.getElementById('monaco-editor-container');
    if (container && !window.monacoEditor) {
        window.monacoEditor = monaco.editor.create(container, {
            value: '# Enter your Python code here\ndef calculate_total(price, quantity):\n    return price * quantity\n\nprint(total_price)',
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            lineNumbers: 'on',
        });
    }
}

// Router
function handleRoute() {
    const hash = window.location.hash || '#/dashboard';
    const app = document.getElementById('app');

    if (!auth.isAuthenticated() && hash !== '#/login' && hash !== '#/register') {
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
        default:
            renderDashboard();
    }
}

// Render Login Page
function renderLogin() {
    document.getElementById('app').innerHTML = `
        <div class="container">
            <div class="card" style="max-width: 400px; margin: 100px auto;">
                <h2 style="margin-bottom: 20px; color: #58a6ff;">Login to BugSense AI</h2>
                <form id="login-form">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Username</label>
                        <input type="text" id="username" required>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Password</label>
                        <input type="password" id="password" required>
                    </div>
                    <button type="submit" style="width: 100%;">Login</button>
                </form>
                <p style="margin-top: 15px; text-align: center;">
                    Don't have an account? <a href="#/register" style="color: #58a6ff;">Register</a>
                </p>
            </div>
        </div>
    `;

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            await api.login(username, password);
            window.location.hash = '#/dashboard';
        } catch (error) {
            alert('Login failed: ' + error.message);
        }
    });
}

// Render Register Page
function renderRegister() {
    document.getElementById('app').innerHTML = `
        <div class="container">
            <div class="card" style="max-width: 400px; margin: 100px auto;">
                <h2 style="margin-bottom: 20px; color: #58a6ff;">Register</h2>
                <form id="register-form">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Username</label>
                        <input type="text" id="username" required>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Email</label>
                        <input type="email" id="email" required>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Password</label>
                        <input type="password" id="password" required>
                    </div>
                    <button type="submit" style="width: 100%;">Register</button>
                </form>
                <p style="margin-top: 15px; text-align: center;">
                    Already have an account? <a href="#/login" style="color: #58a6ff;">Login</a>
                </p>
            </div>
        </div>
    `;

    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        try {
            await api.register(username, email, password);
            window.location.hash = '#/dashboard';
        } catch (error) {
            alert('Registration failed: ' + error.message);
        }
    });
}

// Render Dashboard
async function renderDashboard() {
    try {
        const stats = await api.getDashboardStats();
        document.getElementById('app').innerHTML = `
            <header>
                <div class="container">
                    <nav>
                        <div class="logo">BugSense AI</div>
                        <div>
                            <a href="#/dashboard" class="active">Dashboard</a>
                            <a href="#/workspace">Workspace</a>
                            <a href="#" onclick="auth.logout()">Logout</a>
                        </div>
                    </nav>
                </div>
            </header>
            <div class="container">
                <h1 style="margin-bottom: 30px;">Dashboard</h1>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px;">
                    <div class="card">
                        <h3>Total Sessions</h3>
                        <p style="font-size: 36px; color: #58a6ff;">${stats.total_sessions || 0}</p>
                    </div>
                    <div class="card">
                        <h3>Repairs Attempted</h3>
                        <p style="font-size: 36px; color: #58a6ff;">${stats.repairs_attempted || 0}</p>
                    </div>
                    <div class="card">
                        <h3>Verified Repairs</h3>
                        <p style="font-size: 36px; color: #3fb950;">${stats.verified_repairs || 0}</p>
                    </div>
                    <div class="card">
                        <h3>Failed Verifications</h3>
                        <p style="font-size: 36px; color: #f85149;">${stats.failed_verifications || 0}</p>
                    </div>
                </div>
                <div class="card">
                    <h3 style="margin-bottom: 15px;">Recent Sessions</h3>
                    <button onclick="window.location.hash='#/workspace'" style="margin-bottom: 15px;">New Debugging Session</button>
                    <div id="recent-sessions">
                        <p>No recent sessions yet. Start a new debugging session!</p>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        document.getElementById('app').innerHTML = `
            <div class="container">
                <p style="color: #f85149;">Failed to load dashboard. Please try again.</p>
            </div>
        `;
    }
}

// Render Workspace
function renderWorkspace() {
    document.getElementById('app').innerHTML = `
        <header>
            <div class="container">
                <nav>
                    <div class="logo">BugSense AI</div>
                    <div>
                        <a href="#/dashboard">Dashboard</a>
                        <a href="#/workspace" class="active">Workspace</a>
                        <a href="#" onclick="auth.logout()">Logout</a>
                    </div>
                </nav>
            </div>
        </header>
        <div class="container">
            <h1 style="margin-bottom: 20px;">Debugging Workspace</h1>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <div class="card">
                        <h3 style="margin-bottom: 15px;">Diagnostic Inputs</h3>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Error Message (Optional)</label>
                            <input type="text" id="error-message" placeholder="e.g., NameError: name 'total_price' is not defined">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Terminal Logs (Optional)</label>
                            <textarea id="terminal-logs" rows="3" placeholder="Paste terminal output here..."></textarea>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Language</label>
                            <select id="language">
                                <option value="python">Python</option>
                            </select>
                        </div>
                    </div>
                    <div class="card">
                        <h3 style="margin-bottom: 15px;">Terminal</h3>
                        <div id="terminal-output" class="terminal">No output yet. Click "Run Code" to execute.</div>
                    </div>
                </div>
                <div>
                    <div class="card">
                        <h3 style="margin-bottom: 15px;">Source Code</h3>
                        <div id="monaco-editor-container"></div>
                        <div style="margin-top: 15px; display: flex; gap: 10px;">
                            <button id="run-code-btn" onclick="runCode()">Run Code</button>
                            <button id="analyze-btn" onclick="analyzeCode()">Analyze</button>
                            <button id="repair-btn" onclick="repairCode()">Repair</button>
                            <button onclick="loadExample()">Load Example</button>
                            <button onclick="clearError()">Clear Error</button>
                            <button onclick="clearLogs()">Clear Logs</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    setTimeout(() => {
        loadMonacoEditor();
    }, 100);
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

// Run Code
async function runCode() {
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
    const language = document.getElementById('language').value;
    const terminalOutput = document.getElementById('terminal-output');

    terminalOutput.textContent = 'Running code...';

    try {
        const result = await api.executeCode({
            source_code: code,
            language: language,
            session_id: currentSessionId,
        });

        terminalOutput.textContent = result.stdout || result.stderr || 'No output';
    } catch (error) {
        terminalOutput.textContent = 'Error: ' + error.message;
    }
}

// Analyze Code
async function analyzeCode() {
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
    const errorMessage = document.getElementById('error-message').value;
    const language = document.getElementById('language').value;
    const terminalOutput = document.getElementById('terminal-output');

    terminalOutput.textContent = 'Analyzing code...';

    try {
        const result = await api.analyzeCode({
            source_code: code,
            error_message: errorMessage || 'Unknown error',
            language: language,
            session_id: currentSessionId,
        });

        analysisResult = result;
        terminalOutput.textContent = JSON.stringify(result, null, 2);
    } catch (error) {
        terminalOutput.textContent = 'Error: ' + error.message;
    }
}

// Repair Code
async function repairCode() {
    const code = window.monacoEditor ? window.monacoEditor.getValue() : '';
    const errorMessage = document.getElementById('error-message').value;
    const language = document.getElementById('language').value;
    const terminalOutput = document.getElementById('terminal-output');
    const repairBtn = document.getElementById('repair-btn');

    repairBtn.disabled = true;
    repairBtn.textContent = 'Repairing...';
    terminalOutput.textContent = 'Generating repair...';

    try {
        const result = await api.repairCode({
            source_code: code,
            error_message: errorMessage || 'Unknown error',
            diagnosis: analysisResult || {},
            language: language,
            session_id: currentSessionId,
        });

        let output = `=== Repair Result ===\n`;
        output += `Source: ${result.source}\n`;

        if (result.warning) {
            output += `Warning: ${result.warning}\n`;
        }

        if (result.error) {
            output += `Error: ${result.error}\n`;
        }

        if (result.diff) {
            output += `\n=== Diff ===\n${result.diff}\n`;
        }

        if (result.repaired_code && result.repaired_code !== code) {
            window.pendingRepair = result.repaired_code;
            repairBtn.textContent = 'Apply Repair';
            repairBtn.classList.add('apply-repair-btn');
            repairBtn.disabled = false;
            repairBtn.onclick = applyRepair;
        }

        terminalOutput.textContent = output;
    } catch (error) {
        terminalOutput.textContent = 'Error: ' + error.message;
        repairBtn.disabled = false;
        repairBtn.textContent = 'Repair';
    }
}

// Apply Repair
function applyRepair() {
    if (window.pendingRepair && window.monacoEditor) {
        window.monacoEditor.setValue(window.pendingRepair);
        window.pendingRepair = null;

        const repairBtn = document.getElementById('repair-btn');
        repairBtn.textContent = 'Repair';
        repairBtn.classList.remove('apply-repair-btn');
        repairBtn.onclick = repairCode;

        document.getElementById('terminal-output').textContent += '\n\nRepair applied successfully!';
    }
}

// Clear Error
function clearError() {
    document.getElementById('error-message').value = '';
}

// Clear Logs
function clearLogs() {
    document.getElementById('terminal-logs').value = '';
    document.getElementById('terminal-output').textContent = 'No output yet. Click "Run Code" to execute.';
}

// Initialize
window.addEventListener('hashchange', handleRoute);
window.addEventListener('load', handleRoute);
