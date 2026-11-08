from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CurrentUserView,
    CustomTokenObtainPairView,
    LoginView,
    RegistroView,
)

urlpatterns = [
    # Rutas acordadas en el reparto de responsabilidades
    path("auth/registro/", RegistroView.as_view(), name="auth_registro"),
    path("auth/login/", LoginView.as_view(), name="auth_login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("usuarios/me/", CurrentUserView.as_view(), name="usuarios_me"),

    # Rutas que ya usa el frontend (se mantienen como alias)
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("usuario/login/", LoginView.as_view(), name="usuario_login"),
    path("usuario/me/", CurrentUserView.as_view(), name="usuario_me"),
]
