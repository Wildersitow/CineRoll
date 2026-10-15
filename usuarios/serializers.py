from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "email", "first_name", "last_name"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializador de JWT que añade claims personalizados al token
    y devuelve los datos de usuario que el frontend necesita.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["nombre"] = f"{user.first_name} {user.last_name}".strip() or user.username
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        nombre_completo = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        data["id"] = self.user.id
        data["nombre"] = nombre_completo
        data["email"] = self.user.email
        data["codigo"] = "ABDE456-Lk"
        data["token"] = data["access"]  # Para compatibilidad directa con el frontend
        return data
