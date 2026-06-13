from django.urls import path
from .views import TripPlanAPIView

urlpatterns = [
    path('trip/', TripPlanAPIView.as_view(), name='trip-plan'),
]
