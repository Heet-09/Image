# C:\code\Kreon\image\cbir_app\utils.py
# cbir_app/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('',home, name='home'),
    path('cbir/upload/', upload_image, name='upload_image'),
    path('cbir/search/', search_image, name='search_image'),
    path('cbir/upload/api/',upload_image_api, name='upload_image_api'),
    path('cbir/search/api/',search_image_api, name='search_image_api'),
    # path('api/upload/', )'
    path('cbir/upload/id/',upload_image_id, name='upload_image_id'),
    path('cbir/search/id/',search_image_id, name='search_image_id'),
    path('cbir/upload/id/api/',upload_image_id_api, name='upload_image_id_api'),
    path('cbir/search/id/api/',search_image_id_api, name='search_image_id_api'),
    path('upload_assets/', upload_assets, name='upload_assets'),
]

