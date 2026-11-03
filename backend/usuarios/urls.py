from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import CurrentUserView, CustomTokenObtainPairView, LoginView

urlpatterns = [
    # Endpoints estándar SimpleJWT
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Endpoint de login compatible con React
    path("usuario/login/", LoginView.as_view(), name="usuario_login"),

    # Endpoint para consultar usuario autenticado con JWT
    path("usuario/me/", CurrentUserView.as_view(), name="usuario_me"),
]

