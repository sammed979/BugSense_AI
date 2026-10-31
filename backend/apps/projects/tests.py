from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.dashboard.models import Project, ProjectFile


class ProjectFileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='project-user', password='safe-test-password-42')
        self.other = get_user_model().objects.create_user(username='other-project-user', password='safe-test-password-42')
        self.project = Project.objects.create(user=self.user, name='sample', source_type='paste')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_user_can_save_and_reload_project_text_file(self):
        endpoint = reverse('project_files', kwargs={'project_id': self.project.id})
        saved = self.client.put(endpoint, {'path': 'src/main.py', 'content': 'print(42)'}, format='json')
        self.assertEqual(saved.status_code, 200)
        loaded = self.client.get(endpoint)
        self.assertEqual(loaded.data['files'][0]['content'], 'print(42)')

    def test_project_files_are_user_scoped(self):
        foreign = Project.objects.create(user=self.other, name='private', source_type='paste')
        response = self.client.get(reverse('project_files', kwargs={'project_id': foreign.id}))
        self.assertEqual(response.status_code, 404)

    def test_traversal_paths_are_rejected(self):
        endpoint = reverse('project_files', kwargs={'project_id': self.project.id})
        response = self.client.put(endpoint, {'path': '../outside.py', 'content': 'x'}, format='json')
        self.assertEqual(response.status_code, 400)
