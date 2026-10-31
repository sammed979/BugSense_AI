/**
 * History functionality for BugSense AI
 */

async function loadHistory() {
    try {
        const history = await api.get('/history/api/');

        const list = document.getElementById('history-list');

        if (history.length === 0) {
            list.innerHTML = '<p>No debugging history yet.</p>';
            return;
        }

        list.innerHTML = history.map(item => `
            <div class="history-item">
                <h3>${item.title}</h3>
                <p>Date: ${new Date(item.created_at).toLocaleString()}</p>
                <p>Status: ${item.status}</p>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load history:', error);
        document.getElementById('history-list').innerHTML = '<p class="error-message">Failed to load history</p>';
    }
}
