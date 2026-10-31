/**
 * Learning Centre functionality for BugSense AI
 */

async function loadLearningTopics() {
    try {
        const topics = await api.get('/learning/api/topics/');

        const list = document.getElementById('topics-list');

        if (topics.length === 0) {
            list.innerHTML = '<p>No learning topics available yet.</p>';
            return;
        }

        list.innerHTML = topics.map(topic => `
            <div class="topic-card">
                <span class="category">${topic.category}</span>
                <h3>${topic.title}</h3>
                <p>${topic.description}</p>
                <a href="/learning/topics/${topic.id}/" class="btn btn-secondary">Learn More</a>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load topics:', error);
        document.getElementById('topics-list').innerHTML = '<p class="error-message">Failed to load topics</p>';
    }
}
