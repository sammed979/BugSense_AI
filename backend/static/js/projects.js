/**
 * Projects functionality for BugSense AI
 */

async function loadProjects() {
    try {
        const projects = await api.get('/projects/api/');

        const list = document.getElementById('projects-list');

        if (projects.length === 0) {
            list.innerHTML = '<p>No projects yet. Create your first project!</p>';
            return;
        }

        list.innerHTML = projects.map(project => `
            <div class="project-card">
                <h3>${project.name}</h3>
                <p>${project.description || 'No description'}</p>
                <p>Status: ${project.status}</p>
                <a href="/projects/${project.id}/" class="btn btn-secondary">View</a>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load projects:', error);
        document.getElementById('projects-list').innerHTML = '<p class="error-message">Failed to load projects</p>';
    }
}

document.getElementById('create-project')?.addEventListener('click', () => {
    alert('Create project feature coming soon');
});

document.getElementById('upload-project')?.addEventListener('click', () => {
    alert('ZIP upload feature coming soon');
});
