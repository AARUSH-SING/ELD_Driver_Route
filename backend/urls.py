from django.urls import path, include, re_path
from api.views import HealthCheckAPIView
from backend.views import FrontendView

urlpatterns = [
    path('api/', include('api.urls')),
    path('health/', HealthCheckAPIView.as_view(), name='health'),
    # Catch-all: serve React frontend for all other paths
    re_path(r'^(?!api/|health/|admin/).*', FrontendView.as_view(), name='frontend'),
]
