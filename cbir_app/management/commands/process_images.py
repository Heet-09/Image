# "C:\code\Kreon\image\cbir_app\management\commands\process_images.py"
# import os
# import shutil
# from django.core.management.base import BaseCommand
# from django.conf import settings
# from django.core.files import File
# from cbir_app.models import Image
# from cbir_app.utils import extract_features

# # Define folders
# UPLOAD_FOLDER = os.path.join(settings.MEDIA_ROOT, 'uploads')  # New images location
# PROCESSED_FOLDER = os.path.join(settings.MEDIA_ROOT, 'processed')  # Backup after processing
# IMG_FOLDER = os.path.join(settings.MEDIA_ROOT, 'img')  # Storage for categorized images

# class Command(BaseCommand):
#     help = "Processes images from the upload folder and stores them in the database"

#     def handle(self, *args, **kwargs):
#         if not os.path.exists(UPLOAD_FOLDER):
#             os.makedirs(UPLOAD_FOLDER)

#         if not os.path.exists(PROCESSED_FOLDER):
#             os.makedirs(PROCESSED_FOLDER)

#         # Recursively get all image files inside subdirectories
#         image_files = []
#         for root, _, files in os.walk(UPLOAD_FOLDER):
#             for file in files:
#                 if file.lower().endswith(('.png', '.jpg', '.jpeg')):  # Check for image extensions
#                     image_files.append(os.path.join(root, file))

#         if not image_files:
#             self.stdout.write(self.style.WARNING("No images found in the upload folder."))
#             return

#         for file_path in image_files:
#             filename = os.path.basename(file_path)  # Extract filename
#             company_name = os.path.basename(os.path.dirname(file_path))  # Extract company folder name

#             # Ensure company name is valid
#             if not company_name:
#                 company_name = "None"

#             # Ensure the company folder exists inside 'img'
#             company_folder = os.path.join(IMG_FOLDER, company_name)
#             os.makedirs(company_folder, exist_ok=True)

#             # Move the file to the company folder
#             new_file_path = os.path.join(company_folder, filename)
#             shutil.move(file_path, new_file_path)  # Move file

#             # Extract features
#             feature_data = extract_features(new_file_path)

#             # Save to the database
#             with open(new_file_path, 'rb') as img_file:
#                 django_file = File(img_file)
#                 img_instance = Image(
#                     image=f"img/{company_name}/{filename}",  # Store relative path
#                     company_name=company_name,
#                     pattern_features=feature_data["pattern"],
#                     color_features=feature_data["color"]
#                 )
#                 img_instance.save()

#             # Move processed files to the processed folder for backup
#             shutil.copy(new_file_path, os.path.join(PROCESSED_FOLDER, filename))

#             self.stdout.write(self.style.SUCCESS(f"Processed and stored {filename} under {company_name} successfully!"))


import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from cbir_app.models import Image
from cbir_app.utils import extract_features

# Define folders
UPLOAD_FOLDER = os.path.join(settings.MEDIA_ROOT, 'uploads')  # New images location
PROCESSED_FOLDER = os.path.join(settings.MEDIA_ROOT, 'processed')  # Backup after processing

class Command(BaseCommand):
    help = "Processes images from the upload folder, extracts features, and stores them in the database"

    def handle(self, *args, **kwargs):
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        if not os.path.exists(PROCESSED_FOLDER):
            os.makedirs(PROCESSED_FOLDER)

        # Recursively get all image files inside subdirectories
        image_files = []
        for root, _, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):  # Check for image extensions
                    image_files.append(os.path.join(root, file))

        if not image_files:
            self.stdout.write(self.style.WARNING("No images found in the upload folder."))
            return

        for file_path in image_files:
            filename = os.path.basename(file_path)  # Extract filename
            company_name = os.path.basename(os.path.dirname(file_path))  # Extract company folder name

            # Ensure company name is valid
            if not company_name:
                company_name = "Unknown"

            # Extract features from the image **without saving the file**
            feature_data = extract_features(file_path)

            # Store only features and metadata in the database (no image storage)
            Image.objects.create(
                company_name=company_name,
                pattern_features=feature_data["pattern"],
                color_features=feature_data["color"]
            )

            # Move processed files to the processed folder for backup
            shutil.move(file_path, os.path.join(PROCESSED_FOLDER, filename))

            self.stdout.write(self.style.SUCCESS(f"Processed and stored features of {filename} under {company_name} successfully!"))
