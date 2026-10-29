// BugSense AI - Main Application
let currentSessionId = null;
let currentAttemptId = null;
let analysisResult = null;
window.monacoEditor = null;
window.pendingRepair = null;

// Monaco Editor Loader
let monacoLoaded = false;

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
        window.monacoEditor = monaco.editor.create(container, {
            value: '# Enter your Python code here\ndef calculate_total(price, quantity):\n    return price * quantity\n\nprint(total_price)',
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            lineNumbers: 'on',
            fontSize: 14,
        });
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
            <header>
                <div class="container">
                    <nav>
                        <div class="logo">🔍 BugSense AI</div>
                        <div>
                            <a href="#/dashboard" class="active">Dashboard</a>
                            <a href="#/workspace">Workspace</a>
                            <a href="#" onclick="window.auth.logout()">Logout</a>
                        </div>
                    </nav>
                </div>
            </header>
            <div class="container">
                <h1>Dashboard</h1>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Sessions</h3>
                        <div class="value">${stats.total_sessions || 0}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Repairs Attempted</h3>
                        <div class="value">${stats.repairs_attempted || 0}</div>
                    </div>
                    <div class="stat-card success">
                        <h3>Verified Repairs</h3>
                        <div class="value">${stats.verified_repairs || 0}</div>
                    </div>
                    <div class="stat-card error">
                        <h3>Failed Verifications</h3>
                        <div class="value">${stats.failed_verifications || 0}</div>
                    </div>
                </div>
                <div class="card">
                    <h3>Recent Sessions</h3>
                    <button onclick="window.location.hash='#/workspace'" style="margin-bottom: 16px;">New Debugging Session</button>
                    <div id="recent-sessions">
                        <div class="empty-state">
                            <p>No recent sessions yet.</p>
                            <p>Start a new debugging session to begin!</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        document.getElementById('app').innerHTML = `
            <div class="container">
                <div class="error-message">
                    Failed to load dashboard. Please try again.
                </div>
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
                    <div class="logo">🔍 BugSense AI</div>
                    <div>
                        <a href="#/dashboard">Dashboard</a>
                        <a href="#/workspace" class="active">Workspace</a>
                        <a href="#" onclick="window.auth.logout()">Logout</a>
                    </div>
                </nav>
            </div>
        </header>
        <div class="container">
            <h1>Debugging Workspace</h1>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                <div>
                    <div class="card">
                        <h3>Diagnostic Inputs</h3>
                        <div style="margin-bottom: 16px;">
                            <label>Error Message (Optional)</label>
                            <textarea id="error-message" rows="4" placeholder="e.g., NameError: name 'total_price' is not defined"></textarea>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label>Terminal Logs (Optional)</label>
                            <textarea id="terminal-logs" rows="8" placeholder="Paste terminal output here..."></textarea>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label>Language</label>
                            <select id="language">
                                <option value="python">Python</option>
                            </select>
                        </div>
                    </div>
                    <div class="card">
                        <h3>Terminal Output</h3>
                        <div id="terminal-output" class="terminal">No output yet. Click "Run Code" to execute.</div>
                    </div>
                </div>
                <div>
                    <div class="card">
                        <h3>Source Code</h3>
                        <div id="monaco-editor-container"></div>
                        <div style="margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap;">
                            <button id="run-code-btn" onclick="runCode()">▶ Run Code</button>
                            <button id="analyze-btn" onclick="analyzeCode()">🔍 Analyze</button>
                            <button id="repair-btn" onclick="repairCode()">🔧 Repair</button>
                            <button id="verify-btn" onclick="verifyCode()">✓ Verify</button>
                            <button onclick="loadExample()">📄 Load Example</button>
                            <button onclick="clearError()">✕ Clear Error</button>
                            <button onclick="clearLogs()">🗑️ Clear Logs</button>
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
        const result = await window.api.executeCode({
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
        const result = await window.api.analyzeCode({
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

    if (!code.trim()) {
        terminalOutput.textContent = 'Error: No source code to repair. Please enter code first.';
        return;
    }

    repairBtn.disabled = true;
    repairBtn.textContent = 'Repairing...';
    terminalOutput.textContent = 'Generating repair...';

    try {
        const result = await window.api.repairCode({
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
            terminalOutput.textContent = output;
            repairBtn.disabled = false;
            repairBtn.textContent = 'Repair';
            return;
        }

        if (result.diff) {
            output += `\n=== Diff ===\n${result.diff}\n`;
        }

        if (result.repaired_code && result.repaired_code !== code) {
            window.pendingRepair = {
                original: code,
                repaired: result.repaired_code,
                diff: result.diff,
                source: result.source
            };
            
            output += `\n=== Proposed Repair ===\n`;
            output += result.repaired_code;
            output += `\n\n---\n`;
            output += `Click "Apply Repair" to accept this change, or click "Reject" to keep the original code.`;
            
            repairBtn.textContent = 'Apply Repair';
            repairBtn.classList.add('apply-repair-btn');
            repairBtn.disabled = false;
            repairBtn.onclick = applyRepair;
            
            // Add Reject button
            const btnContainer = repairBtn.parentElement;
            if (!document.getElementById('reject-btn')) {
                const rejectBtn = document.createElement('button');
                rejectBtn.id = 'reject-btn';
                rejectBtn.textContent = 'Reject';
                rejectBtn.style.background = '#EF4444';
                rejectBtn.onclick = rejectRepair;
                btnContainer.appendChild(rejectBtn);
            }
        } else {
            output += `\nNo changes were made to the code.`;
            repairBtn.disabled = false;
            repairBtn.textContent = 'Repair';
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
        window.monacoEditor.setValue(window.pendingRepair.repaired);
        window.pendingRepair = null;

        const repairBtn = document.getElementById('repair-btn');
        repairBtn.textContent = 'Repair';
        repairBtn.classList.remove('apply-repair-btn');
        repairBtn.disabled = false;
        repairBtn.onclick = repairCode;

        // Remove Reject button
        const rejectBtn = document.getElementById('reject-btn');
        if (rejectBtn) {
            rejectBtn.remove();
        }

        const terminalOutput = document.getElementById('terminal-output');
        terminalOutput.textContent += '\n\n✓ Repair applied successfully! Click "Run Code" to verify.';
    }
}

// Reject Repair
function rejectRepair() {
    window.pendingRepair = null;

    const repairBtn = document.getElementById('repair-btn');
    repairBtn.textContent = 'Repair';
    repairBtn.classList.remove('apply-repair-btn');
    repairBtn.disabled = false;
    repairBtn.onclick = repairCode;

    // Remove Reject button
    const rejectBtn = document.getElementById('reject-btn');
    if (rejectBtn) {
        rejectBtn.remove();
    }

    const terminalOutput = document.getElementById('terminal-output');
    terminalOutput.textContent += '\n\n✗ Repair rejected. Original code preserved.';
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
    verifyBtn.textContent = 'Verifying...';
    terminalOutput.textContent = 'Running verification checks...';

    try {
        // Run the code to verify it executes
        const result = await window.api.executeCode({
            source_code: code,
            language: language,
            session_id: currentSessionId,
        });

        let output = `=== Verification Result ===\n`;
        output += `Exit Code: ${result.exit_code}\n`;
        output += `Duration: ${result.duration_ms}ms\n\n`;

        if (result.exit_code === 0) {
            output += `✓ Status: VERIFIED\n`;
            output += `✓ Code executed successfully\n`;
            if (result.stdout) {
                output += `\n=== Output ===\n${result.stdout}`;
            }
        } else {
            output += `✗ Status: FAILED\n`;
            output += `✗ Code execution failed\n`;
            if (result.stderr) {
                output += `\n=== Error Output ===\n${result.stderr}`;
            }
        }

        if (result.timed_out) {
            output += `\n⚠ Warning: Execution timed out`;
        }

        terminalOutput.textContent = output;
    } catch (error) {
        terminalOutput.textContent = 'Error: ' + error.message;
    } finally {
        verifyBtn.disabled = false;
        verifyBtn.textContent = '✓ Verify';
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
