/**
 * Workspace functionality for BugSense AI
 */

let editor;

function initWorkspace() {
    // Load Monaco Editor
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});

    require(['vs/editor/editor.main'], function() {
        editor = monaco.editor.create(document.getElementById('monaco-editor'), {
            value: '# Paste your Python code here\n\ndef example():\n    return "Hello, World!"\n\nprint(example())',
            language: 'python',
            theme: 'vs-light',
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
        });
    });

    // Event listeners
    document.getElementById('clear-code').addEventListener('click', clearCode);
    document.getElementById('load-example').addEventListener('click', loadExample);
    document.getElementById('clear-error').addEventListener('click', () => {
        document.getElementById('error-message').value = '';
    });
    document.getElementById('clear-logs').addEventListener('click', () => {
        document.getElementById('terminal-logs').value = '';
    });
    document.getElementById('clear-output').addEventListener('click', clearOutput);
    document.getElementById('run-code').addEventListener('click', runCode);
    document.getElementById('analyze-error').addEventListener('click', analyzeError);
    document.getElementById('autofix-verify').addEventListener('click', autoFixVerify);
}

function clearCode() {
    if (editor) {
        editor.setValue('');
    }
}

function loadExample() {
    if (editor) {
        editor.setValue(`def calculate_total():
    price = 100
    quantity = 3
    return total

print(calculate_total())`);
    }
}

function clearOutput() {
    document.getElementById('output-content').textContent = '';
}

function appendOutput(text, isError = false) {
    const output = document.getElementById('output-content');
    output.textContent += text + '\n';
    output.style.color = isError ? '#ef4444' : '#d4d4d4';
}

async function runCode() {
    const code = editor ? editor.getValue() : '';
    if (!code.trim()) {
        alert('Please enter some code to run');
        return;
    }

    clearOutput();
    appendOutput('Running code...', false);

    try {
        const response = await api.post('/execution/executions/', {
            code: code,
            language: 'python'
        });

        if (response.stdout) {
            appendOutput(response.stdout, false);
        }
        if (response.stderr) {
            appendOutput(response.stderr, true);
        }
        appendOutput(`Exit code: ${response.exit_code}`, false);
    } catch (error) {
        appendOutput(`Error: ${error.message}`, true);
    }
}

async function analyzeError() {
    const code = editor ? editor.getValue() : '';
    const errorMessage = document.getElementById('error-message').value;
    const terminalLogs = document.getElementById('terminal-logs').value;

    if (!code.trim()) {
        alert('Please enter some code to analyze');
        return;
    }

    try {
        const response = await api.post('/analysis/analyses/', {
            title: 'New Analysis',
            source_code: code,
            error_message: errorMessage,
            terminal_logs: terminalLogs,
            language: 'python'
        });

        displayDiagnosis(response);
    } catch (error) {
        alert(`Analysis failed: ${error.message}`);
    }
}

async function autoFixVerify() {
    const code = editor ? editor.getValue() : '';
    const errorMessage = document.getElementById('error-message').value;
    const terminalLogs = document.getElementById('terminal-logs').value;

    if (!code.trim()) {
        alert('Please enter some code to fix');
        return;
    }

    try {
        // First create an analysis
        const analysis = await api.post('/analysis/analyses/', {
            title: 'AutoFix Analysis',
            source_code: code,
            error_message: errorMessage,
            terminal_logs: terminalLogs,
            language: 'python'
        });

        // Then trigger repair
        const repair = await api.post(`/analysis/analyses/${analysis.id}/repair/`);

        displayRepair(repair);
    } catch (error) {
        alert(`AutoFix failed: ${error.message}`);
    }
}

function displayDiagnosis(data) {
    const section = document.getElementById('diagnosis-section');
    const content = document.getElementById('diagnosis-content');

    section.style.display = 'block';
    content.innerHTML = `
        <p><strong>Root Cause:</strong> ${data.root_cause || 'Analysis pending...'}</p>
        <p><strong>Confidence:</strong> ${data.confidence || 'N/A'}</p>
        <p><strong>Proposed Solution:</strong> ${data.proposed_solution || 'Pending...'}</p>
    `;
}

function displayRepair(data) {
    const section = document.getElementById('repair-section');
    const content = document.getElementById('repair-content');

    section.style.display = 'block';
    content.innerHTML = `
        <p><strong>Status:</strong> ${data.status || 'Pending'}</p>
        <p><strong>Proposed Changes:</strong></p>
        <pre>${JSON.stringify(data.proposed_patch, null, 2)}</pre>
    `;
}
