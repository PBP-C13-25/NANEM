from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError

from ..models import PlantCollection
from .serializers import PlantCollectionSerializer

class WrappedValidationExceptionMixin:
    """Membungkus error validasi ke dalam key 'errors'."""
    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(exc, ValidationError) and response is not None:
            response.data = {"errors": response.data}
        return response

class CollectionListCreateAPIView(WrappedValidationExceptionMixin, generics.ListCreateAPIView):
    serializer_class = PlantCollectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = (
            PlantCollection.objects
            .select_related("owner")
            .prefetch_related("likes")
            .order_by("-created_at")
        )
        owner_id = self.request.query_params.get("owner")
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class CollectionDetailAPIView(WrappedValidationExceptionMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PlantCollectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = (
            PlantCollection.objects
            .select_related("owner")
            .prefetch_related("likes")
        )
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            queryset = queryset.filter(owner=self.request.user)
        return queryset

class ToggleLikeAPIView(WrappedValidationExceptionMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(PlantCollection, pk=pk)
        if post.likes.filter(pk=request.user.pk).exists():
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