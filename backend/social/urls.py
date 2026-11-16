from django.urls import path

from social.views import (
    ListaDetailView,
    ListaElementoDetailView,
    ListaElementoListCreateView,
    ListaListCreateView,
    MediaResenaListCreateView,
    MiResenaMediaView,
    ResenaDetailView,
    UsuarioListasListView,
)

urlpatterns = [
    path(
        "media/<int:media_id>/resenas/propia/",
        MiResenaMediaView.as_view(),
        name="media-resenas-propia",
    ),
    path(
        "media/<int:media_id>/resena-propia/",
        MiResenaMediaView.as_view(),
        name="media-resena-propia",
    ),
    path(
        "media/<int:media_id>/resenas/me/",
        MiResenaMediaView.as_view(),
        name="media-resenas-me",
    ),
    path(
        "media/<int:media_id>/resenas/",
        MediaResenaListCreateView.as_view(),
        name="media-resenas",
    ),
    path("resenas/<int:pk>/", ResenaDetailView.as_view(), name="resena-detail"),
    # Endpoints de listas
    path("listas/", ListaListCreateView.as_view(), name="lista-list-create"),
    path("listas/<int:pk>/", ListaDetailView.as_view(), name="lista-detail"),
    path(
        "listas/<int:lista_id>/elementos/",
        ListaElementoListCreateView.as_view(),
        name="lista-elementos",
    ),
    path(
        "listas/<int:lista_id>/elementos/<int:media_id>/",
        ListaElementoDetailView.as_view(),
        name="lista-elemento-detail",
    ),
    path(
        "usuarios/<str:username>/listas/",
        UsuarioListasListView.as_view(),
        name="usuario-listas",
    ),
]

