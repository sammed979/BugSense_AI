const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const apiSource = fs.readFileSync(path.join(__dirname, '..', 'js', 'api.js'), 'utf8');

function makeApi(fetchImpl, hostname = '127.0.0.1', token = null) {
  const storage = new Map();
  if (token) storage.set('access_token', token);
  const window = {
    location: { protocol: 'http:', hostname, hash: '' },
    BUGSENSE_API_BASE_URL: undefined,
    auth: { clearTokens() { storage.delete('access_token'); storage.delete('refresh_token'); } },
  };
  const context = {
    window,
    localStorage: { getItem(key) { return storage.get(key) || null; }, setItem(key, value) { storage.set(key, value); }, removeItem(key) { storage.delete(key); } },
    fetch: fetchImpl,
    AbortController,
    URL,
    setTimeout,
    clearTimeout,
    console,
  };
  vm.runInNewContext(apiSource, context, { filename: 'api.js' });
  return window.api;
}

test('register posts the serializer fields to the shared backend URL', async () => {
  let request;
  const api = makeApi(async (url, options) => {
    request = { url, options };
    throw new TypeError('Failed to fetch');
  });

  await assert.rejects(
    api.register('sam', 'sam@example.test', 'Blue-Cedar-River-927!', 'Blue-Cedar-River-927!'),
    /Cannot reach the BugSense backend at http:\/\/127\.0\.0\.1:8000/
  );
  assert.equal(request.url, 'http://127.0.0.1:8000/api/v1/auth/register/');
  assert.deepEqual(JSON.parse(request.options.body), {
    username: 'sam',
    email: 'sam@example.test',
    password: 'Blue-Cedar-River-927!',
    confirm_password: 'Blue-Cedar-River-927!',
  });
});

test('LogSense sends only the provided log and explicit consent to the authenticated API', async () => {
  let request;
  const api = makeApi(async (url, options) => {
    request = { url, options };
    return { status: 200, ok: true, async json() { return { source: 'local_patterns' }; } };
  }, '127.0.0.1', 'access-token');
  await api.explainLog({ log: 'ERROR test', explanation_level: 'beginner', explanation_language: 'en', allow_external_ai: false });
  assert.equal(request.url, 'http://127.0.0.1:8000/api/v1/analysis/logsense/');
  assert.equal(request.options.headers.Authorization, 'Bearer access-token');
  assert.equal(JSON.parse(request.options.body).allow_external_ai, false);
});

test('expired access token refreshes and retries the authenticated history request', async () => {
  const storage = new Map();
  let historyCalls = 0;
  let retryAuthorization;
  const window = {
    location: { protocol: 'http:', hostname: '127.0.0.1', hash: '' },
    auth: { clearTokens() { storage.clear(); } },
  };
  storage.set('access_token', 'expired-access');
  storage.set('refresh_token', 'valid-refresh');
  const context = {
    window,
    localStorage: { getItem(key) { return storage.get(key) || null; }, setItem(key, value) { storage.set(key, value); }, removeItem(key) { storage.delete(key); } },
    fetch: async (url, options = {}) => {
      if (url.endsWith('/auth/token/refresh/')) {
        return { ok: true, status: 200, async json() { return { access: 'fresh-access', refresh: 'fresh-refresh' }; } };
      }
      historyCalls += 1;
      if (historyCalls === 1) return { ok: false, status: 401, async json() { return { detail: 'expired' }; } };
      retryAuthorization = options.headers.Authorization;
      return { ok: true, status: 200, async json() { return { sessions: [] }; } };
    },
    AbortController, URL, setTimeout, clearTimeout, console,
  };
  vm.runInNewContext(apiSource, context, { filename: 'api.js' });
  const result = await window.api.getHistory();
  assert.deepEqual(JSON.parse(JSON.stringify(result)), { sessions: [] });
  assert.equal(retryAuthorization, 'Bearer fresh-access');
  assert.equal(historyCalls, 2);
});

test('backend network failure returns a useful startup message', async () => {
  const api = makeApi(async () => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(
    api.register('sam', 'sam@example.test', 'Blue-Cedar-River-927!', 'Blue-Cedar-River-927!'),
    /python manage\.py runserver 127\.0\.0\.1:8000/
  );
});

test('localhost frontend uses the IPv4 Django loopback address', async () => {
  let requestedUrl;
  const api = makeApi(async (url) => {
    requestedUrl = url;
    throw new TypeError('Failed to fetch');
  }, 'localhost');
  await assert.rejects(api.register('sam', 'sam@example.test', 'Strong-Pass-927!', 'Strong-Pass-927!'));
  assert.equal(requestedUrl, 'http://127.0.0.1:8000/api/v1/auth/register/');
});

test('history request sends the stored Bearer token and accepts the Django sessions envelope', async () => {
  let request;
  const api = makeApi(async (url, options) => {
    request = { url, options };
    return { ok: true, status: 200, async json() { return { sessions: [{ id: 17 }] }; } };
  }, '127.0.0.1', 'access-token-test');

  const response = await api.getHistory();
  assert.equal(request.url, 'http://127.0.0.1:8000/api/v1/history/');
  assert.equal(request.options.headers.Authorization, 'Bearer access-token-test');
  assert.deepEqual(JSON.parse(JSON.stringify(response)), { sessions: [{ id: 17 }] });
});

test('history authentication failure is not returned as an empty successful response', async () => {
  const api = makeApi(async () => ({ ok: false, status: 401, async json() { return { detail: 'Authentication credentials were not provided.' }; } }), '127.0.0.1', 'expired-token');
  await assert.rejects(api.getHistory(), /session expired/i);
});

test('LogSense uses the registered trailing-slash route and reports a real backend 404 clearly', async () => {
  let requested;
  const api = makeApi(async (url) => { requested = url; return { ok: false, status: 404, async json() { return {}; } }; }, '127.0.0.1', 'access-token');
  await assert.rejects(api.explainLog({ log: 'ERROR' }), /LogSense API endpoint was not found/);
  assert.equal(requested, 'http://127.0.0.1:8000/api/v1/analysis/logsense/');
});

test('learning lesson, exercise, quiz, dashboard, filters and recommendations use authenticated endpoints', async () => {
  const requests=[];
  const api=makeApi(async(url,options={})=>{requests.push({url,options});return {ok:true,status:200,async json(){return {recommendations:[],sessions:[]};}};},'127.0.0.1','learning-token');
  await api.getLearningTopics({q:'NameError',difficulty:'beginner'});
  await api.getLearningDashboard();
  await api.getLearningLesson(4);
  await api.updateLearningProgress(4,{bookmarked:true});
  await api.submitLearningExercise(4,{root_cause:'name missing',proposed_fix:'define it'});
  await api.submitLearningQuiz(4,[0]);
  await api.getLearningRecommendations({error_type:'NameError',message:'total_price is undefined'});
  assert.deepEqual(requests.map(item=>new URL(item.url).pathname.replace('/api/v1','')), [
    '/learning/','/learning/dashboard/','/learning/lessons/4/','/learning/lessons/4/','/learning/lessons/4/exercise/','/learning/lessons/4/quiz/','/learning/recommendations/'
  ]);
  assert.ok(requests.every(item=>item.options.headers.Authorization==='Bearer learning-token'));
  assert.match(requests[0].url,/q=NameError&difficulty=beginner/);
});

test('concurrent opens of one lesson share a single in-flight request', async () => {
  let calls = 0;
  let resolveFetch;
  const api = makeApi(async () => {
    calls += 1;
    return new Promise(resolve => { resolveFetch = () => resolve({ ok: true, status: 200, async json() { return { id: 11, error_name: 'NameError' }; } }); });
  }, '127.0.0.1', 'learning-token');
  const first = api.getLearningLesson(11);
  const second = api.getLearningLesson(11);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 1);
  resolveFetch();
  assert.deepEqual(await Promise.all([first, second]), [{ id: 11, error_name: 'NameError' }, { id: 11, error_name: 'NameError' }]);
});

test('a missing lesson is reported as missing content, not as a missing API route', async () => {
  const api = makeApi(async () => ({ ok: false, status: 404, async json() { return { detail: 'Not found.' }; } }), '127.0.0.1', 'learning-token');
  await assert.rejects(api.getLearningLesson(99999), /debugging lesson was not found/i);
});
