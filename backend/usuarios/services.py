from usuarios.serializers import CustomTokenObtainPairSerializer


def nombre_completo(usuario):
    return f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username


def generar_payload_autenticacion(usuario):
    """Tokens JWT + datos básicos del usuario, con el formato que consume el frontend."""
    refresh = CustomTokenObtainPairSerializer.get_token(usuario)
    access = str(refresh.access_token)
    return {
        "id": usuario.id,
        "username": usuario.username,
        "nombre": nombre_completo(usuario),
        "email": usuario.email,
        "token": access,
        "access": access,
        "refresh": str(refresh),
    }
