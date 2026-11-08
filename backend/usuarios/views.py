from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CustomTokenObtainPairSerializer,
    PerfilSerializer,
    RegistroSerializer,
)
from .services import generar_payload_autenticacion

Usuario = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Endpoint estándar DRF SimpleJWT con claims personalizados (/api/token/)"""
    serializer_class = CustomTokenObtainPairSerializer


class RegistroView(APIView):
    """
    Registro de usuarios (/api/auth/registro/).
    Recibe { username, email, password, first_name?, last_name? } y responde 201
    con los mismos datos que el login, para que el frontend inicie sesión directo.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(
            generar_payload_autenticacion(usuario),
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    Endpoint de login compatible con React (/api/usuario/login/ y /api/auth/login/)
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

        # Buscar por username o por correo (sin distinguir mayúsculas)
        username = username_or_email
        if "@" in username_or_email:
            candidato = Usuario.objects.filter(email__iexact=username_or_email).first()
            username = candidato.username if candidato else None

        user = authenticate(username=username, password=password) if username else None

        if user is None:
            return Response(
                {"error": "Credenciales incorrectas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(generar_payload_autenticacion(user), status=status.HTTP_200_OK)


class CurrentUserView(RetrieveUpdateAPIView):
    """
    Perfil del usuario autenticado (/api/usuario/me/ y /api/usuarios/me/).
    GET para verlo y PATCH/PUT para editar nombre, correo, avatar y biografía.
    Requiere encabezado: Authorization: Bearer <access_token>
    """
    serializer_class = PerfilSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
