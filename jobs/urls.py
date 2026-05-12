from django.urls import path
from .views import ScrapeJobView

urlpatterns = [
    path('scrape/', ScrapeJobView.as_view()),
]