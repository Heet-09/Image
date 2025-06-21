import os
import pandas as pd
from django.core.management.base import BaseCommand
from cbir_app.models import ImageFeature
from cbir_app.utils import extract_features

class Command(BaseCommand):
    help = "Import image metadata and extract features from Excel + image folder"

    def add_arguments(self, parser):
        parser.add_argument('--excel_path', type=str, required=True, help='Path to the Excel file')
        parser.add_argument('--image_folder', type=str, required=True, help='Path to the folder containing images')

    def handle(self, *args, **options):
        excel_path = options['excel_path']
        image_folder = options['image_folder']

        # Load Excel
        try:
            df = pd.read_excel(excel_path)
        except Exception as e:
            self.stderr.write(f"Error reading Excel: {e}")
            return

        # Validate required columns
        required_columns = {"image_filename", "image_ref_id", "company_id"}
        if not required_columns.issubset(df.columns):
            self.stderr.write(f"Missing required columns: {required_columns - set(df.columns)}")
            return

        total_rows = len(df)
        imported_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            image_filename = row["image_filename"]
            image_path = os.path.join(image_folder, str(image_filename))
            image_ref_id = int(row["image_ref_id"])
            company_id = int(row["company_id"])

            if not os.path.exists(image_path):
                self.stderr.write(f"Image not found: {image_path}")
                continue

            if ImageFeature.objects.filter(company_id=company_id, image_ref_id=image_ref_id).exists():
                self.stdout.write(f"Skipped existing entry: {company_id}-{image_ref_id}")
                skipped_count += 1
                continue

            try:
                features = extract_features(image_path)

                filters = {
                    f'filter_{i}': row.get(f'filter_{i}', '').strip() if pd.notna(row.get(f'filter_{i}')) else ''
                    for i in range(1, 11)
                }

                ImageFeature.objects.create(
                    company_id=company_id,
                    image_ref_id=image_ref_id,
                    pattern_features=features["pattern"],
                    color_features=features["color"],
                    **filters
                )
                self.stdout.write(self.style.SUCCESS(f"Imported {image_filename}"))
                imported_count += 1

            except Exception as e:
                self.stderr.write(f"Failed to import {image_filename}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Import completed: {imported_count} added, {skipped_count} skipped out of {total_rows} rows."))
