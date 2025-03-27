# C:\code\Kreon\image\cbir_app\views.py
# cbir_app/views.py
from django.shortcuts import render, redirect
from .models import Image
from .utils import extract_features, find_similar_images
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
import os
import tempfile
import glob

@csrf_exempt
def upload_image(request):
    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        folder_path = request.POST.get("folder_path", "").strip()

        if not company_name:
            return render(request, "cbir_app/upload_image.html", {"error": "Company name is required."})
        
        if not os.path.exists(folder_path):
            return render(request, "cbir_app/upload_image.html", {"error": "Invalid folder path."})

        image_files = glob.glob(os.path.join(folder_path, "*.[jpJP][pnPN]*[gG]"))  # Get JPG/PNG images

        if not image_files:
            return render(request, "cbir_app/upload_image.html", {"error": "No images found in the folder."})

        for image_path in image_files:
            try:
                feature_data = extract_features(image_path)

                Image.objects.create(
                    company_name=company_name,
                    pattern_features=feature_data["pattern"],
                    color_features=feature_data["color"]
                )
            except Exception as e:
                print(f"Error processing {image_path}: {e}")

        return redirect('upload_image')

    return render(request, "cbir_app/upload_image.html")

@csrf_exempt
def search_image(request):
    if request.method == "POST":
        query_image_file = request.FILES['image']

        # Create a temporary file to save the uploaded image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(query_image_file.read())  # Save uploaded file
            temp_file_path = temp_file.name  # Get the temp file path

        try:
            # Extract features from the saved image file
            query_features = extract_features(temp_file_path)

            # Fetch all stored feature vectors from the database
            images = Image.objects.all()
            database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

            if not database_features:
                return render(request, 'cbir_app/search_results.html', {
                    'query_image_url': None,
                    'pattern_results': [],
                    'color_results': []
                })

            # Find similar images
            similarities = find_similar_images(query_features, database_features, top_k=5)

            pattern_results = [
                {
                    "company_name": images[int(idx)].company_name,
                    "score": similarities["pattern"]["scores"][i],
                    "image_id": images[int(idx)].image_id,
                }
                for i, idx in enumerate(similarities["pattern"]["indices"])
            ]

            color_results = [
                {
                    "company_name": images[int(idx)].company_name,
                    "score": similarities["color"]["scores"][i],
                    "image_id": images[int(idx)].image_id,
                }
                for i, idx in enumerate(similarities["color"]["indices"])
            ]

            return render(request, 'cbir_app/search_results.html', {
                'query_image_url': None,  # No image stored, only features
                'pattern_results': pattern_results,
                'color_results': color_results,
            })

        finally:
            # Remove the temporary file to free up space
            os.remove(temp_file_path)

    return render(request, 'cbir_app/search_image.html')


