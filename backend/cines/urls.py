urlpatterns = []
from django.urls import path

from cines.views import CineListView, MediaFuncionListView


urlpatterns = [
    path("cines/", CineListView.as_view(), name="cine-list"),
    path(
        "media/<int:media_id>/funciones/",
        MediaFuncionListView.as_view(),
        name="media-funciones",
    ),
]
