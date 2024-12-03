# cbir_app/models.py
from django.db import models

class Image(models.Model):
    image = models.ImageField(upload_to='img/')
    features = models.JSONField()  # To store extracted features as JSON
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image {self.image.name}"
