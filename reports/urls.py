# reports/urls.py

from django.urls import path
from .views import ReportsView

urlpatterns = [
    path("summary", ReportsView.as_view()),
]