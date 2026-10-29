from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, UserProfileView, logout_view

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register_api'),
    path('login/', TokenObtainPairView.as_view(), name='login_api'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout_api'),
    path('me/', UserProfileView.as_view(), name='user_profile'),
]
