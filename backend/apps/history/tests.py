from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from datetime import timedelta
from rest_framework_simplejwt.tokens import AccessToken

from apps.dashboard.models import DebuggingSession


class HistoryContractTests(APITestCase):
    def test_invalid_and_expired_bearer_tokens_are_rejected(self):
        user = get_user_model().objects.create_user(username='token-user', password='safe-test-password-42')
        expired = AccessToken.for_user(user)
        expired.set_exp(lifetime=timedelta(seconds=-1))
        for token in ('not-a-jwt', str(expired)):
            with self.subTest(token_kind='expired' if token == str(expired) else 'invalid'):
                response = self.client.get(reverse('history_list'), HTTP_AUTHORIZATION=f'Bearer {token}')
                self.assertEqual(response.status_code, 401)

    def test_list_returns_owned_sessions_in_sessions_envelope(self):
        user = get_user_model().objects.create_user(username='history-user', password='safe-test-password-42')
        other = get_user_model().objects.create_user(username='other-user', password='safe-test-password-42')
        own_session = DebuggingSession.objects.create(user=user, source_code='print(1)', language='python')
        DebuggingSession.objects.create(user=other, source_code='print(2)', language='python')
        self.client.force_authenticate(user)

        response = self.client.get(reverse('history_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data['sessions']], [own_session.id])

    def test_detail_route_is_nested_under_sessions(self):
        user = get_user_model().objects.create_user(username='open-user', password='safe-test-password-42')
        session = DebuggingSession.objects.create(user=user, source_code='print(500)', language='python')
        self.client.force_authenticate(user)

        response = self.client.get(reverse('session_detail', kwargs={'session_id': session.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['source_code'], 'print(500)')

    def test_search_and_language_filters_are_applied(self):
        user = get_user_model().objects.create_user(username='filter-user', password='safe-test-password-42')
        DebuggingSession.objects.create(user=user, language='python', error_message='NameError: missing value')
        DebuggingSession.objects.create(user=user, language='java', error_message='NullPointerException')
        self.client.force_authenticate(user)
        response = self.client.get(reverse('history_list'), {'search': 'NameError', 'language': 'python'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['sessions'][0]['error_summary'], 'NameError: missing value')
