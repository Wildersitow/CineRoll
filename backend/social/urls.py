from django.urls import path

from social.seguimiento import (
    FeedActividadView,
    SeguidoresListView,
    SeguirUsuarioView,
    SiguiendoListView,
)
from social.views import (
    AprobarSugerenciaView,
    ListaDetailView,
    ListaElementoDetailView,
    ListaElementoListCreateView,
    ListaListCreateView,
    MediaMisListasView,
    MediaResenaListCreateView,
    MediaResenaResumenView,
    MediaSugerenciaListCreateView,
    MiRegistroMediaView,
    MiResenaMediaView,
    MisListasView,
    RechazarSugerenciaView,
    ResenasListView,
    ResenaDetailView,
    ReportarResenaView,
    SugerenciasModeracionView,
    UsuarioListasListView,
)

urlpatterns = [
    path("resenas/", ResenasListView.as_view(), name="resenas-list"),
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
        "media/<int:media_id>/resenas/resumen/",
        MediaResenaResumenView.as_view(),
        name="media-resenas-resumen",
    ),
    path(
        "media/<int:media_id>/resenas/",
        MediaResenaListCreateView.as_view(),
        name="media-resenas",
    ),
    path(
        "resenas/<int:pk>/reportar/",
        ReportarResenaView.as_view(),
        name="resena-reportar",
    ),
    path("resenas/<int:pk>/", ResenaDetailView.as_view(), name="resena-detail"),

    # Estado del título en las listas del usuario autenticado
    path(
        "media/<int:media_id>/mis-listas/",
        MediaMisListasView.as_view(),
        name="media-mis-listas",
    ),

    # Endpoints de listas
    path(
        "media/<int:media_id>/mi-registro/",
        MiRegistroMediaView.as_view(),
        name="media-mi-registro",
    ),
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

    # Rutas para el usuario actual (/me/) - DEBEN ir antes de <str:username>
    path(
        "usuarios/me/feed/",
        FeedActividadView.as_view(),
        name="usuario-feed",
    ),
    path(
        "usuarios/me/listas/",
        MisListasView.as_view(),
        name="usuarios-me-listas",
    ),

    # Rutas por username de otros usuarios
    path(
        "usuarios/<str:username>/seguir/",
        SeguirUsuarioView.as_view(),
        name="usuario-seguir",
    ),
    path(
        "usuarios/<str:username>/seguidores/",
        SeguidoresListView.as_view(),
        name="usuario-seguidores",
    ),
    path(
        "usuarios/<str:username>/siguiendo/",
        SiguiendoListView.as_view(),
        name="usuario-siguiendo",
    ),
    path(
        "usuarios/<str:username>/listas/",
        UsuarioListasListView.as_view(),
        name="usuario-listas",
    ),
    path(
        "media/<int:media_id>/sugerencias/",
        MediaSugerenciaListCreateView.as_view(),
        name="media-sugerencias",
    ),
    path(
        "sugerencias/",
        SugerenciasModeracionView.as_view(),
        name="sugerencias-moderacion",
    ),
    path(
        "sugerencias/<int:pk>/aprobar/",
        AprobarSugerenciaView.as_view(),
        name="sugerencia-aprobar",
    ),
    path(
        "sugerencias/<int:pk>/rechazar/",
        RechazarSugerenciaView.as_view(),
        name="sugerencia-rechazar",
    ),
]

