from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()
REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'
VALID_PASSWORD = 'Blue-Cedar-River-927!'


class RegistrationFlowTests(APITestCase):
    def payload(self, **overrides):
        data = {
            'username': 'bugsense-new-user',
            'email': 'new-user@example.test',
            'password': VALID_PASSWORD,
            'confirm_password': VALID_PASSWORD,
        }
        data.update(overrides)
        return data

    def test_registration_creates_user_and_user_can_log_in(self):
        response = self.client.post(REGISTER_URL, self.payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.get(username='bugsense-new-user').check_password(VALID_PASSWORD))
        self.assertNotIn('password', response.data)

        login = self.client.post(LOGIN_URL, {
            'username': 'bugsense-new-user',
            'password': VALID_PASSWORD,
        }, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn('access', login.data)
        self.assertIn('refresh', login.data)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.client.post(REGISTER_URL, self.payload(), format='json')
        response = self.client.post(REGISTER_URL, self.payload(
            username='another-user', email='NEW-USER@example.test'
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_username_is_rejected(self):
        self.client.post(REGISTER_URL, self.payload())
        response = self.client.post(REGISTER_URL, self.payload(email='second@example.test'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_is_rejected(self):
        response = self.client.post(REGISTER_URL, self.payload(
            password='password', confirm_password='password'
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertFalse(User.objects.filter(username='bugsense-new-user').exists())

    def test_missing_required_fields_are_rejected(self):
        response = self.client.post(REGISTER_URL, {'username': 'missing-fields'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)
        self.assertIn('confirm_password', response.data)

    def test_malformed_json_is_rejected(self):
        response = self.client.generic('POST', REGISTER_URL, data='{not-json', content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(
        CORS_ALLOWED_ORIGINS=['http://127.0.0.1:5173'],
        CORS_ALLOW_ALL_ORIGINS=False,
    )
    def test_vite_development_origin_passes_cors_preflight(self):
        response = self.client.options(REGISTER_URL, HTTP_ORIGIN='http://127.0.0.1:5173',
                                       HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
                                       HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type')
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://127.0.0.1:5173')


class ProviderPreferencesTests(APITestCase):
    def test_preferences_persist_without_exposing_credentials(self):
        user = User.objects.create_user(username='provider-user', password=VALID_PASSWORD)
        self.client.force_authenticate(user)
        endpoint = '/api/v1/auth/ai-provider/'
        loaded = self.client.get(endpoint)
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.data['mode'], 'gemini')
        self.assertIn('provider_status', loaded.data)
        self.assertNotIn('api_key', loaded.data)
        saved = self.client.patch(endpoint, {'mode': 'local', 'primary_provider': 'gemini', 'secondary_provider': 'openai'}, format='json')
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.get(endpoint).data['mode'], 'local')

    def test_profile_can_update_display_name_and_email(self):
        user = User.objects.create_user(username='profile-user', password=VALID_PASSWORD, email='old@example.test')
        self.client.force_authenticate(user)
        response = self.client.patch('/api/v1/auth/me/', {'first_name': 'Sam', 'email': 'new@example.test'}, format='json')
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Sam')
        self.assertEqual(user.email, 'new@example.test')
