from django.urls import path

from cines.views import (
    CineDetailView,
    CineFuncionListView,
    CineListView,
    CarteleraEstadoView,
    FuncionListView,
    MediaFuncionListView,
)


urlpatterns = [
    path("cartelera/estado/", CarteleraEstadoView.as_view(), name="cartelera-estado"),
    path("cines/", CineListView.as_view(), name="cine-list"),
    path("cines/<int:pk>/", CineDetailView.as_view(), name="cine-detail"),
    path(
        "cines/<int:cine_id>/funciones/",
        CineFuncionListView.as_view(),
        name="cine-funciones",
    ),
    path("funciones/", FuncionListView.as_view(), name="funcion-list"),
    path(
        "media/<int:media_id>/funciones/",
        MediaFuncionListView.as_view(),
        name="media-funciones",
    ),
]
