# C:\code\Kreon\image\cbir_app\utils.py
# cbir_app/models.py
from django.db import models


class Image(models.Model):
    image = models.ImageField(upload_to='img/')
    image_id = models.PositiveIntegerField(default=None,null=True,)
    company_name = models.CharField(max_length=255, default=None)  # Store company name
    pattern_features = models.JSONField(default=list)  # Store pattern features
    color_features = models.JSONField(default=list)    # Store color features
    uploaded_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.company_name} - {self.image.name}"


class ImageFeature(models.Model):
    image_id = models.PositiveIntegerField(default=1)
    company_name = models.CharField(max_length=255, default=None)  # Store company name
    pattern_features = models.JSONField(default=list)  # Store pattern features
    color_features = models.JSONField(default=list)    # Store color features
    uploaded_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.company_name} - {self.image_id}"