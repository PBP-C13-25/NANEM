from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from ..models import PlantCollection
from .serializers import PlantCollectionSerializer
from .permissions import IsOwnerOrReadOnly


class CollectionListAPIView(generics.ListAPIView):
    serializer_class = PlantCollectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            PlantCollection.objects
            .select_related("owner")
            .prefetch_related("likes")
            .order_by("-created_at")
        )


class CollectionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PlantCollectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            PlantCollection.objects
            .select_related("owner")
            .prefetch_related("likes")
        )


class CollectionCreateAPIView(generics.CreateAPIView):
    serializer_class = PlantCollectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CollectionUpdateAPIView(generics.UpdateAPIView):
    serializer_class = PlantCollectionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return (
            PlantCollection.objects
            .select_related("owner")
            .prefetch_related("likes")
        )


class CollectionDeleteAPIView(generics.DestroyAPIView):
    serializer_class = PlantCollectionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return PlantCollection.objects.all()


class ToggleLikeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(PlantCollection, pk=pk)
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            is_liked = False
        else:
            post.likes.add(request.user)
            is_liked = True

        return Response(
            {
                "is_liked": is_liked,
                "like_count": post.total_likes()
            },
            status=status.HTTP_200_OK
        )