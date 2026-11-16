from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, UserProfileView, logout_view, AIProviderSettingsView, CustomTokenObtainPairView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register_api'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login_api'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout_api'),
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('ai-provider/', AIProviderSettingsView.as_view(), name='ai_provider_settings'),
]
