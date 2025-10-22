# Create this file: cbir_app/management/commands/regenerate_features.py
# First create directories: cbir_app/management/ and cbir_app/management/commands/
# Add __init__.py files in both directories

from django.core.management.base import BaseCommand
from django.conf import settings
import os
from cbir_app.models import Image
from cbir_app.utils import extract_features

class Command(BaseCommand):
    help = 'Regenerate features for all existing images'

    def handle(self, *args, **options):
        images = Image.objects.all()
        total = images.count()
        
        self.stdout.write(f'Regenerating features for {total} images...')
        
        updated = 0
        errors = 0
        
        for i, image in enumerate(images, 1):
            try:
                # Construct full path
                image_path = os.path.join(settings.MEDIA_ROOT, image.image.name)
                
                if os.path.exists(image_path):
                    # Extract new features
                    feature_data = extract_features(image_path)
                    
                    # Update the image
                    image.pattern_features = feature_data["pattern"]
                    image.color_features = feature_data["color"]
                    image.save()
                    
                    updated += 1
                    self.stdout.write(f'Progress: {i}/{total} - Updated: {image.image.name}')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'File not found: {image_path}')
                    )
                    errors += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {image.image.name}: {str(e)}')
                )
                errors += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed! Updated: {updated}, Errors: {errors}'
            )
        )   