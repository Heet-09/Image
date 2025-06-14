# C:\code\Kreon\image\cbir_app\utils.py
# cbir_app/models.py
from django.db import models


class Image(models.Model):
    image = models.ImageField(upload_to='img/')
    image_id = models.PositiveIntegerField(default=None,null=True,)
    company_id = models.PositiveIntegerField(default=1)   # Store company name
    pattern_features = models.JSONField(default=list)  # Store pattern features
    color_features = models.JSONField(default=list)    # Store color features
    filter_1 = models.CharField(max_length=100, blank=True)
    filter_2 = models.CharField(max_length=100, blank=True)
    filter_3 = models.CharField(max_length=100, blank=True)
    filter_4 = models.CharField(max_length=100, blank=True)
    filter_5 = models.CharField(max_length=100, blank=True)
    filter_6 = models.CharField(max_length=100, blank=True)
    filter_7 = models.CharField(max_length=100, blank=True)
    filter_8 = models.CharField(max_length=100, blank=True)
    filter_9 = models.CharField(max_length=100, blank=True)
    filter_10 = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.company_id} - {self.image.name}"


class ImageFeature(models.Model):
    image_ref_id = models.BigIntegerField(default=1)
    company_id = models.PositiveIntegerField(default=1, db_index=True)  # Store company name
    pattern_features = models.JSONField(default=list)  # Store pattern features
    color_features = models.JSONField(default=list)    # Store color features
    filter_1 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_2 = models.CharField(max_length=100, blank=True, db_index=True)
    filter_3 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_4 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_5 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_6 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_7 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_8 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_9 = models.CharField(max_length=100, blank=True,db_index=True)
    filter_10 = models.CharField(max_length=100, blank=True,db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'image_ref_id'], name='unique_company_image')
        ]
        indexes = [
            models.Index(fields=['company_id', 'image_ref_id'], name='company_image_idx')
        ]
    def __str__(self):
        return f"{self.company_id} - {self.image_ref_id}"
    