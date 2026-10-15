from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from media.models import Genero, Media
from media.serializers import (
	GeneroSerializer,
	MediaDetailSerializer,
	MediaListSerializer,
)


class MediaListView(ListAPIView):
	queryset = Media.objects.prefetch_related("generos")
	serializer_class = MediaListSerializer
	permission_classes = (AllowAny,)


class MediaDetailView(RetrieveAPIView):
	queryset = Media.objects.prefetch_related("generos", "creditos__persona")
	serializer_class = MediaDetailSerializer
	permission_classes = (AllowAny,)


class GeneroListView(ListAPIView):
	queryset = Genero.objects.all()
	serializer_class = GeneroSerializer
	permission_classes = (AllowAny,)
