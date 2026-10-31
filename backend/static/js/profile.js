/**
 * Profile functionality for BugSense AI
 */

document.getElementById('profile-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const firstName = document.getElementById('first_name').value;
    const lastName = document.getElementById('last_name').value;

    try {
        await api.patch('/auth/api/me/', {
            first_name: firstName,
            last_name: lastName
        });
        alert('Profile updated successfully');
    } catch (error) {
        alert(`Failed to update profile: ${error.message}`);
    }
});

document.getElementById('delete-account')?.addEventListener('click', () => {
    if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
        alert('Account deletion feature coming soon');
    }
});
