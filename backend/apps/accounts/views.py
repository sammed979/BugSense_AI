from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserRegistrationSerializer, UserSerializer, AIProviderSettingsSerializer
from .models import AIProviderSettings
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class AIProviderSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = AIProviderSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        defaults = {'mode': 'gemini', 'primary_provider': 'gemini', 'secondary_provider': 'openai', 'automatic_fallback': False}
        return AIProviderSettings.objects.get_or_create(user=self.request.user, defaults=defaults)[0]

    def _status(self, response):
        # Expose readiness only. Credential values always remain server-side.
        mode = response.data.get('mode')
        selected = response.data.get('primary_provider') if mode == 'automatic' else mode
        response.data['provider_status'] = {
            'gemini': bool(getattr(settings, 'GEMINI_API_KEY', '')),
            'openai': bool(getattr(settings, 'OPENAI_API_KEY', '')),
        }
        response.data['active_provider'] = selected
        return response

    def retrieve(self, request, *args, **kwargs):
        return self._status(super().retrieve(request, *args, **kwargs))

    def update(self, request, *args, **kwargs):
        return self._status(super().update(request, *args, **kwargs))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout view - clears client-side token."""
    return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
