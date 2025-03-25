# C:\code\Kreon\image\cbir_app\utils.py
# cbir_app/urls.py
from django.urls import path
from .views import upload_image, search_image

urlpatterns = [
    path('upload/', upload_image, name='upload_image'),
    path('search/', search_image, name='search_image'),
]

