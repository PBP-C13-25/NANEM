from django.urls import path

from . import views
from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.RecommendationFormView.as_view(), name="index"),
    path("result/", views.RecommendationResultView.as_view(), name="result"),
    path("save/", views.SaveHistoryView.as_view(), name="save"),
    path("history/", views.HistoryListView.as_view(), name="history_list"),
    path("history/<int:pk>/", views.HistoryDetailView.as_view(), name="history_detail"),
    path("history/<int:pk>/edit/", views.HistoryUpdateView.as_view(), name="history_update"),
    path("history/<int:pk>/delete/", views.HistoryDeleteView.as_view(), name="history_delete"),
]

