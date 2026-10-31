const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const appSource = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

function loadApp() {
  const window = { addEventListener() {}, location: { hash: '' }, auth: { isAuthenticated() { return true; } } };
  const document = { getElementById() { return null; }, querySelectorAll() { return []; } };
  const context = { window, document, console, setTimeout, clearTimeout };
  vm.runInNewContext(appSource, context, { filename: 'app.js' });
  return { window, context };
}

test('history response normalizer accepts Django sessions and paginated formats', () => {
  const { context } = loadApp();
  assert.deepEqual(Array.from(context.normalizeHistoryResponse({ sessions: [{ id: 1 }] })), [{ id: 1 }]);
  assert.deepEqual(Array.from(context.normalizeHistoryResponse({ results: [{ id: 2 }] })), [{ id: 2 }]);
  assert.throws(() => context.normalizeHistoryResponse({ detail: 'Unauthorized' }), /unexpected response/);
});

test('LogSense route and controls provide independent log analysis, consent, levels, languages, and follow-up actions', () => {
  assert.match(appSource, /case '#\/logsense'/);
  assert.match(appSource, /id="ls-input"/);
  assert.match(appSource, /id="ls-consent"/);
  assert.match(appSource, /id="ls-level"/);
  assert.match(appSource, /id="ls-language"/);
  assert.match(appSource, /Ask a follow-up about this log/);
  assert.match(appSource, /data-learn="practice"/);
  assert.match(appSource, /data-learn="word"/);
  assert.match(appSource, /data-learn="fix"/);
  assert.match(appSource, /Explain This Output/);
  assert.match(appSource, /explanationInProgress/);
  assert.match(appSource, /ls-paste/);
  assert.match(appSource, /dragover/);
});

test('Learning Centre is an error-first searchable practice hub with saved progress and LogSense links', () => {
  assert.match(appSource,/Error-based learning paths/);
  assert.match(appSource,/learning-search/);
  assert.match(appSource,/learning-category/);
  assert.match(appSource,/lesson-hint-button/);
  assert.match(appSource,/submitLearningExercise/);
  assert.match(appSource,/submitLearningQuiz/);
  assert.match(appSource,/getLearningDashboard/);
  assert.match(appSource,/getLearningRecommendations/);
  assert.match(appSource,/Practise this error/);
  assert.match(appSource,/Reveal next hint/);
});

test('workspace code state reads and updates the textarea fallback', () => {
  const fallback = { value: 'print(500)' };
  const document = { getElementById(id) { return id === 'workspace-code-fallback' ? fallback : null; } };
  const window = { bugSenseWorkspaceCode: 'stale', monacoEditor: null, addEventListener() {} };
  const context = { window, document };
  vm.runInNewContext(appSource, context, { filename: 'app.js' });
  assert.equal(context.getEditorCode(), 'print(500)');
  context.setEditorCode('print(1 + 499)');
  assert.equal(fallback.value, 'print(1 + 499)');
  assert.equal(window.bugSenseWorkspaceCode, 'print(1 + 499)');
});

test('Monaco AMD modules initialize one editor only after the editor module callback', async () => {
  let requireModuleCalls = 0;
  let editorCreations = 0;
  const container = { id: 'monaco-editor-container', style: {} };
  const editor = {
    getDomNode() { return { isConnected: true }; },
    getValue() { return 'print(500)'; },
    layout() {},
    dispose() {},
    onDidChangeModelContent() { return { dispose() {} }; },
  };
  function amdRequire(modules, ready) {
    if (Array.isArray(modules)) { requireModuleCalls += 1; ready(); }
  }
  amdRequire.config = () => {};
  const window = {
    addEventListener() {},
    require: amdRequire,
    bugSenseWorkspaceCode: 'print(500)',
    monaco: { editor: { create() { editorCreations += 1; return editor; } } },
  };
  const document = {
    getElementById(id) { return id === 'monaco-editor-container' ? container : null; },
    querySelector() { return null; },
  };
  class ResizeObserver { observe() {} disconnect() {} }
  const context = { window, document, ResizeObserver, setTimeout, clearTimeout };
  vm.runInNewContext(appSource, context, { filename: 'app.js' });

  await context.loadMonacoEditor();
  await context.loadMonacoEditor();
  assert.equal(requireModuleCalls, 1);
  assert.equal(editorCreations, 1);
  assert.equal(window.monacoEditor, editor);
});
