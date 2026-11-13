// Runtime configuration for BugSense AI
// Automatically detects environment based on hostname
const hostname = window.location.hostname;

let API_BASE_URL = 'http://localhost:8000/api/v1';
let ENVIRONMENT = 'development';

if (hostname === 'localhost' || hostname === '127.0.0.1') {
    // Local development
    API_BASE_URL = 'http://localhost:8000/api/v1';
    ENVIRONMENT = 'development';
} else if (hostname.includes('.vercel.app')) {
    // Production on Vercel
    API_BASE_URL = process.env.RENDER_BACKEND_URL || 'https://your-backend.onrender.com/api/v1';
    ENVIRONMENT = 'production';
} else if (hostname.includes('.onrender.com')) {
    // Production on Render
    API_BASE_URL = 'https://your-backend.onrender.com/api/v1';
    ENVIRONMENT = 'production';
}

window.BugSenseConfig = {
    API_BASE_URL: API_BASE_URL,
    ENVIRONMENT: ENVIRONMENT,
    VERSION: '1.0.0'
};
