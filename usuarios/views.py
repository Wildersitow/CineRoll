from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import CustomTokenObtainPairSerializer, UsuarioSerializer

Usuario = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Endpoint estándar DRF SimpleJWT con claims personalizados (/api/token/)"""
    serializer_class = CustomTokenObtainPairSerializer


class LoginView(APIView):
    """
    Endpoint de login compatible con React (/api/usuario/login/)
    Acepta { usuario, clave } o { username, password }
    Genera tokens JWT y retorna datos de perfil + token
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username_or_email = request.data.get("usuario") or request.data.get("username", "")
        password = request.data.get("clave") or request.data.get("password", "")

        username_or_email = str(username_or_email).strip()

        if not username_or_email or not password:
            return Response(
                {"error": "Debe proporcionar usuario y clave."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Intentar buscar por username o email
        user = None
        if "@" in username_or_email:
            try:
                user_obj = Usuario.objects.get(email__iexact=username_or_email)
                user = authenticate(username=user_obj.username, password=password)
            except Usuario.DoesNotExist:
                user = None
        else:
            user = authenticate(username=username_or_email, password=password)

        if user is None:
            return Response(
                {"error": "Credenciales incorrectas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {"error": "Usuario inactivo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Generar tokens con SimpleJWT
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        nombre_completo = f"{user.first_name} {user.last_name}".strip() or user.username

        return Response(
            {
                "id": user.id,
                "nombre": nombre_completo,
                "email": user.email,
                "codigo": "ABDE456-Lk",
                "token": access_token,
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )

