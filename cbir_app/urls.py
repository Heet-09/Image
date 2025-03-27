from django.urls import path
from .views import upload_image, search_image

urlpatterns = [
    path('api/upload/', upload_image, name='api_upload_image'),
    path('api/search/', search_image, name='api_search_image'),
]
