from django.urls import path

from media.views import (
	GeneroDetailView,
	GeneroListView,
	MediaDetailView,
	MediaListView,
	PersonaDetailView,
	PersonaListView,
)


urlpatterns = [
	path("media/", MediaListView.as_view(), name="media-list"),
	path("media/<int:pk>/", MediaDetailView.as_view(), name="media-detail"),
	path("generos/", GeneroListView.as_view(), name="genero-list"),
	path("generos/<int:pk>/", GeneroDetailView.as_view(), name="genero-detail"),
	path("personas/", PersonaListView.as_view(), name="persona-list"),
	path("personas/<int:pk>/", PersonaDetailView.as_view(), name="persona-detail"),
]
