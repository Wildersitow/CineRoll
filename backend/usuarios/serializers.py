from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

Usuario = get_user_model()

MENSAJE_EMAIL_REPETIDO = "Ya existe una cuenta con este correo."


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
        return Usuario.objects.create_user(**validated_data)


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