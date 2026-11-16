from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserRegistrationSerializer, UserSerializer, AIProviderSettingsSerializer
from .models import AIProviderSettings, default_ai_provider_settings
from django.contrib.auth import get_user_model
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

User = get_user_model()


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer


@method_decorator(csrf_exempt, name='dispatch')
class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view that exempts CSRF for JWT authentication."""
    pass


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class AIProviderSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = AIProviderSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return AIProviderSettings.objects.get_or_create(
            user=self.request.user,
            defaults=default_ai_provider_settings(),
        )[0]

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
