from django.urls import path

from . import views

app_name = "recommendations_api"

urlpatterns = [
    path("recommendations/", views.RecommendationAPIView.as_view(), name="recommend"),
    path("history/", views.HistoryListAPIView.as_view(), name="history_list"),
    path("history/<int:pk>/", views.HistoryDetailAPIView.as_view(), name="history_detail"),
]
