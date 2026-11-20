from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from social.models import Lista, Seguimiento

Usuario = get_user_model()

MENSAJE_EMAIL_REPETIDO = "Ya existe una cuenta con este correo."
NOMBRES_RESERVADOS = {
    "me",
    "admin",
    "api",
    "root",
    "soporte",
    "staff",
    "superuser",
    "cineroll",
    "ayuda",
    "null",
    "undefined",
    "perfil",
    "usuarios",
}



def _email_unico():
    return UniqueValidator(
        queryset=Usuario.objects.all(),
        lookup="iexact",
        message=MENSAJE_EMAIL_REPETIDO,
    )


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "email", "first_name", "last_name"]


class PerfilSerializer(serializers.ModelSerializer):
    """Perfil propio (/api/usuarios/me/): se puede editar todo menos usuario y permisos."""

    nombre = serializers.SerializerMethodField()
    email = serializers.EmailField(required=False, validators=[_email_unico()])

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nombre",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "biografia",
            "escala_calificacion",
            "is_staff",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "is_staff", "date_joined"]

    def get_nombre(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def validate_email(self, value):
        return value.strip().lower()


class PerfilPublicoSerializer(serializers.ModelSerializer):
    """Perfil público visible para cualquier usuario o visitante."""

    nombre = serializers.SerializerMethodField()
    total_resenas = serializers.SerializerMethodField()
    promedio_puntuacion_dada = serializers.SerializerMethodField()
    total_seguidores = serializers.SerializerMethodField()
    total_siguiendo = serializers.SerializerMethodField()
    lo_sigo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nombre",
            "avatar",
            "biografia",
            "escala_calificacion",
            "date_joined",
            "total_resenas",
            "promedio_puntuacion_dada",
            "total_seguidores",
            "total_siguiendo",
            "lo_sigo",
        ]
        read_only_fields = fields

    def get_nombre(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_total_resenas(self, obj):
        return obj.resenas.visibles().count()

    def get_promedio_puntuacion_dada(self, obj):
        avg = obj.resenas.visibles().aggregate(models.Avg("puntuacion"))["puntuacion__avg"]
        return None if avg is None else round(float(avg), 2)

    def get_total_seguidores(self, obj):
        if hasattr(obj, "total_seguidores"):
            return obj.total_seguidores
        return obj.seguidores.count()

    def get_total_siguiendo(self, obj):
        if hasattr(obj, "total_siguiendo"):
            return obj.total_siguiendo
        return obj.siguiendo.count()

    def get_lo_sigo(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return None
        if request.user.pk == obj.pk:
            return False
        if hasattr(obj, "lo_sigo_anotado"):
            return bool(obj.lo_sigo_anotado)
        return Seguimiento.objects.filter(seguidor=request.user, seguido=obj).exists()



class CambioPasswordSerializer(serializers.Serializer):
    """Permite al usuario autenticado cambiar su contraseña validando la anterior."""

    clave_actual = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )
    clave_nueva = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )
    old_password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    def validate(self, attrs):
        usuario = self.context["request"].user
        clave_actual = attrs.get("clave_actual") or attrs.get("old_password")
        clave_nueva = attrs.get("clave_nueva") or attrs.get("new_password")

        if not clave_actual:
            raise serializers.ValidationError(
                {"clave_actual": ["Debe proporcionar la contraseña actual."]}
            )
        if not clave_nueva:
            raise serializers.ValidationError(
                {"clave_nueva": ["Debe proporcionar la nueva contraseña."]}
            )

        if not usuario.check_password(clave_actual):
            raise serializers.ValidationError(
                {"clave_actual": ["La contraseña actual es incorrecta."]}
            )

        try:
            validate_password(clave_nueva, usuario)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"clave_nueva": list(exc.messages)})

        attrs["clave_nueva"] = clave_nueva
        return attrs

    def save(self, **kwargs):
        usuario = self.context["request"].user
        nueva_clave = self.validated_data["clave_nueva"]
        usuario.set_password(nueva_clave)
        usuario.save()
        return usuario


class RegistroSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[_email_unico()])
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = Usuario
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "escala_calificacion",
        ]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "escala_calificacion": {"required": False},
        }

    def validate_username(self, value):
        nombre_limpio = value.strip()
        if nombre_limpio.lower() in NOMBRES_RESERVADOS:
            raise serializers.ValidationError(
                "Este nombre de usuario no está disponible."
            )
        if Usuario.objects.filter(username__iexact=nombre_limpio).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con este nombre de usuario."
            )
        return nombre_limpio

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        # Se valida con un usuario temporal para que aplique el validador de
        # "contraseña demasiado parecida al usuario/correo".
        candidato = Usuario(**{k: v for k, v in attrs.items() if k != "password"})
        try:
            validate_password(attrs["password"], candidato)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            usuario = Usuario.objects.create_user(**validated_data)
            Lista.objects.get_or_create(
                usuario=usuario,
                tipo=Lista.Tipo.FAVORITAS,
                defaults={"nombre": "Favoritas", "publica": True},
            )
            Lista.objects.get_or_create(
                usuario=usuario,
                tipo=Lista.Tipo.POR_VER,
                defaults={"nombre": "Por ver", "publica": True},
            )
            return usuario



class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializador de JWT que añade claims personalizados al token
    y devuelve los datos de usuario que el frontend necesita.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        nombre_completo = f"{user.first_name} {user.last_name}".strip() or user.username
        token["username"] = user.username
        token["nombre"] = nombre_completo
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        nombre_completo = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        data["id"] = self.user.id
        data["username"] = self.user.username
        data["nombre"] = nombre_completo
        data["email"] = self.user.email
        data["token"] = data["access"]  # Para compatibilidad directa con el frontend
        return data