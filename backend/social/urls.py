from django.urls import path

from social.views import (
    MediaResenaListCreateView,
    MiResenaMediaView,
    ResenaDetailView,
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
]
