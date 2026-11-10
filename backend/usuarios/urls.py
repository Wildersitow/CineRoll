from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CambiarPasswordView,
    CurrentUserView,
    CustomTokenObtainPairView,
    LoginView,
    LogoutView,
    MisResenasView,
    PerfilPublicoView,
    RegistroView,
    UsuarioResenasPublicasView,
)

urlpatterns = [
    # Rutas de autenticación
    path("auth/registro/", RegistroView.as_view(), name="auth_registro"),
    path("auth/login/", LoginView.as_view(), name="auth_login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
    path("auth/cambiar-clave/", CambiarPasswordView.as_view(), name="auth_cambiar_clave"),

    # Perfil propio y gestión de cuenta
    path("usuarios/me/", CurrentUserView.as_view(), name="usuarios_me"),
    path("usuarios/me/clave/", CambiarPasswordView.as_view(), name="usuarios_me_clave"),
    path("usuarios/me/password/", CambiarPasswordView.as_view(), name="usuarios_me_password"),
    path("usuarios/me/resenas/", MisResenasView.as_view(), name="usuarios_me_resenas"),

    # Perfil público y reseñas de otros usuarios
    path("usuarios/<int:pk>/", PerfilPublicoView.as_view(), name="usuarios_perfil_publico_id"),
    path("usuarios/<str:username>/", PerfilPublicoView.as_view(), name="usuarios_perfil_publico"),
    path("usuarios/<int:pk>/resenas/", UsuarioResenasPublicasView.as_view(), name="usuarios_resenas_publicas_id"),
    path("usuarios/<str:username>/resenas/", UsuarioResenasPublicasView.as_view(), name="usuarios_resenas_publicas"),

    # Rutas que ya usa el frontend (se mantienen como alias)
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("usuario/login/", LoginView.as_view(), name="usuario_login"),
    path("usuario/logout/", LogoutView.as_view(), name="usuario_logout"),
    path("usuario/me/", CurrentUserView.as_view(), name="usuario_me"),
    path("usuario/me/clave/", CambiarPasswordView.as_view(), name="usuario_me_clave"),
    path("usuario/me/resenas/", MisResenasView.as_view(), name="usuario_me_resenas"),
]
