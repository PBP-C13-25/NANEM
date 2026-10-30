from . import views
from django.urls import path

from . import views

app_name = "collection"

urlpatterns = [
    path('', views.CollectionListView.as_view(), name='index'),
    path('create/', views.CollectionCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CollectionDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.CollectionUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.CollectionDeleteView.as_view(), name='delete'),
    path('<int:pk>/like/', views.ToggleLikeView.as_view(), name='like'),
]

