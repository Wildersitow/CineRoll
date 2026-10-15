from django.urls import path

from media.views import GeneroListView, MediaDetailView, MediaListView


urlpatterns = [
	path("media/", MediaListView.as_view(), name="media-list"),
	path("media/<int:pk>/", MediaDetailView.as_view(), name="media-detail"),
	path("generos/", GeneroListView.as_view(), name="genero-list"),
]
