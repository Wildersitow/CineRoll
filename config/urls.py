from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/", include("media.urls")),
    path("api/", include("cines.urls")),
    path("api/", include("social.urls")),
    path("api/", include("usuarios.urls")),
]