# Generated by Django 5.2 on 2025-05-17 17:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cbir_app', '0012_alter_image_image_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='image',
            old_name='color_features',
            new_name='color_feature',
        ),
    ]
