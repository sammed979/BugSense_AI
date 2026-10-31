/**
 * Authentication functions for BugSense AI
 */

function initLoginForm() {
    const form = document.getElementById('login-form');
    const errorDiv = document.getElementById('error-message');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        try {
            const response = await api.post('/auth/api/login/', {
                email,
                password,
            });

            // Store tokens
            api.setToken(response.access);
            localStorage.setItem('refresh_token', response.refresh);

            // Redirect to dashboard
            window.location.href = '/dashboard';
        } catch (error) {
            errorDiv.textContent = error.message || 'Login failed. Please check your credentials.';
            errorDiv.classList.add('show');
        }
    });
}

function initRegisterForm() {
    const form = document.getElementById('register-form');
    const errorDiv = document.getElementById('error-message');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const password_confirm = document.getElementById('password_confirm').value;

        // Validate passwords match
        if (password !== password_confirm) {
            errorDiv.textContent = 'Passwords do not match.';
            errorDiv.classList.add('show');
            return;
        }

        try {
            await api.post('/auth/api/register/', {
                username,
                email,
                password,
            });

            // Registration successful, redirect to login
            window.location.href = '/login?registered=true';
        } catch (error) {
            errorDiv.textContent = error.message || 'Registration failed. Please try again.';
            errorDiv.classList.add('show');
        }
    });
}

function logout() {
    api.clearToken();
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
}
