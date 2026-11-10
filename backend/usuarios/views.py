from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from social.models import Resena
from social.serializers import ResenaSerializer

from .serializers import (
    CambioPasswordSerializer,
    CustomTokenObtainPairSerializer,
    PerfilPublicoSerializer,
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
            raise ValidationError(
                "Debe proporcionar usuario y clave.", code="datos_incompletos"
            )

        # Buscar por username o por correo (sin distinguir mayúsculas)
        username = username_or_email
        if "@" in username_or_email:
            candidato = Usuario.objects.filter(email__iexact=username_or_email).first()
            username = candidato.username if candidato else None

        user = authenticate(username=username, password=password) if username else None

        if user is None:
            raise ValidationError(
                "Credenciales incorrectas.", code="credenciales_invalidas"
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


class LogoutView(APIView):
    """
    Cierra la sesión de forma segura invalidando el refresh token en la lista negra.
    POST /api/auth/logout/ o /api/usuario/logout/
    Recibe: { "refresh": "<refresh_token>" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ValidationError(
                {"refresh": "Debe proporcionar el token de refresco (refresh)."},
                code="datos_incompletos",
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except (TokenError, InvalidToken):
            raise ValidationError(
                {"refresh": "Token inválido, expirado o ya revocado."},
                code="token_invalido",
            )
        return Response(
            {"mensaje": "Sesión cerrada correctamente."},
            status=status.HTTP_200_OK,
        )


class CambiarPasswordView(APIView):
    """
    Cambio de contraseña desde el perfil del usuario autenticado.
    POST/PUT a /api/usuarios/me/clave/ (o alias /api/auth/cambiar-clave/, /api/usuarios/me/password/).
    Requiere: { "clave_actual": "...", "clave_nueva": "..." } (o old_password / new_password).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambioPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(
            {
                "mensaje": "Contraseña actualizada exitosamente.",
                **generar_payload_autenticacion(usuario),
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        return self.post(request)


class PerfilPublicoView(RetrieveAPIView):
    """
    Perfil público de un usuario (para visitantes y otros usuarios).
    GET /api/usuarios/<id>/ o /api/usuarios/<username>/
    """
    serializer_class = PerfilPublicoSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        identificador = (
            self.kwargs.get("identificador")
            or self.kwargs.get("pk")
            or self.kwargs.get("username")
        )
        if str(identificador).isdigit():
            return get_object_or_404(Usuario, pk=int(identificador))
        return get_object_or_404(Usuario, username__iexact=str(identificador))


class UsuarioResenasPublicasView(ListAPIView):
    """
    Lista pública y paginada de reseñas escritas por un usuario.
    GET /api/usuarios/<id>/resenas/ o /api/usuarios/<username>/resenas/
    """
    serializer_class = ResenaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        identificador = (
            self.kwargs.get("identificador")
            or self.kwargs.get("pk")
            or self.kwargs.get("username")
        )
        if str(identificador).isdigit():
            usuario = get_object_or_404(Usuario, pk=int(identificador))
        else:
            usuario = get_object_or_404(Usuario, username__iexact=str(identificador))
        return (
            Resena.objects.visibles()
            .filter(usuario=usuario)
            .select_related("media", "usuario")
            .order_by("-fecha_creacion", "-id")
        )


class MisResenasView(ListAPIView):
    """
    Reseñas propias del usuario autenticado para mostrar en su perfil.
    GET /api/usuarios/me/resenas/
    """
    serializer_class = ResenaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Resena.objects.visibles()
            .filter(usuario=self.request.user)
            .select_related("media", "usuario")
            .order_by("-fecha_creacion", "-id")
        )
