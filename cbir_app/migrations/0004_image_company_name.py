# Generated by Django 5.1.4 on 2025-03-22 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cbir_app', '0003_remove_image_features_image_color_features_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='company_name',
            field=models.CharField(default='sparsh', max_length=255),
        ),
    ]
