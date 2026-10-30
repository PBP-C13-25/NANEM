from .models import PlantCollection

def get_user_collections(user):
    """
    Mengembalikan queryset koleksi milik user tertentu
    """
    return (
        PlantCollection.objects
        .filter(owner=user)
        .select_related("owner")
        .prefetch_related("likes")
        .order_by("-created_at")
    )