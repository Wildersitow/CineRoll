from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    # El correo es opcional pero, si existe, único. Se guarda NULL (no "") cuando
    # está vacío para que varios usuarios sin correo no choquen con la restricción.
    email = models.EmailField("correo electrónico", unique=True, null=True, blank=True)
    avatar = models.URLField(blank=True)
    biografia = models.TextField(blank=True, max_length=500)

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower() or None
        super().save(*args, **kwargs)
