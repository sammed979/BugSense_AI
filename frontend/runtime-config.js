(() => {
    const hostname = window.location.hostname;

    let runtimeApiBaseUrl = 'http://localhost:8000/api/v1';
    let environment = 'development';

    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        runtimeApiBaseUrl = 'http://localhost:8000/api/v1';
        environment = 'development';
    } else if (hostname.endsWith('.vercel.app')) {
        runtimeApiBaseUrl = 'https://bugsense-ai-mulk.onrender.com/api/v1';
        environment = 'production';
    } else if (hostname.endsWith('.onrender.com')) {
        runtimeApiBaseUrl = 'https://bugsense-ai-mulk.onrender.com/api/v1';
        environment = 'production';
    }

    window.BugSenseConfig = Object.freeze({
        API_BASE_URL: runtimeApiBaseUrl,
        ENVIRONMENT: environment,
        VERSION: '1.0.0'
    });
})();
