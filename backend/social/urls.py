from django.urls import path

from social.views import MediaResenaListCreateView, ResenaDetailView

urlpatterns = [
    path(
        "media/<int:media_id>/resenas/",
        MediaResenaListCreateView.as_view(),
        name="media-resenas",
    ),
    path("resenas/<int:pk>/", ResenaDetailView.as_view(), name="resena-detail"),
]
