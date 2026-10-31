/**
 * Dashboard functionality for BugSense AI
 */

async function loadDashboardStats() {
    try {
        const stats = await api.get('/dashboard/stats/');

        document.getElementById('total-analyses').textContent = stats.total_analyses;
        document.getElementById('total-repairs').textContent = stats.total_repair_attempts;
        document.getElementById('verified-repairs').textContent = stats.verified_repairs;
        document.getElementById('success-rate').textContent = (stats.repair_success_rate * 100).toFixed(1) + '%';

        // Load recent activity
        loadRecentActivity();
    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
        document.getElementById('recent-activity').innerHTML = '<p class="error-message">Failed to load stats. Please try again.</p>';
    }
}

async function loadRecentActivity() {
    try {
        // For now, show a placeholder
        document.getElementById('recent-activity').innerHTML = '<p>No recent activity</p>';
    } catch (error) {
        console.error('Failed to load recent activity:', error);
    }
}
