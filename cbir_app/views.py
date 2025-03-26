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

# def upload_image(request):
    # if request.method == "POST" and request.FILES.getlist('images'):
    #     company_name = request.POST.get("company_name").strip()
    #     if not company_name:
    #         return render(request, "cbir_app/upload_image.html", {"error": "Company name is required."})
        
    #     image_id = request.POST.get("image_id")


    #     # Define folder path based on company name
    #     company_folder = os.path.join(settings.MEDIA_ROOT, 'img', company_name)
    #     os.makedirs(company_folder, exist_ok=True)

    #     fs = FileSystemStorage(location=company_folder)

    #     for image_file in request.FILES.getlist('images'):
    #         filename = fs.save(image_file.name, image_file)
    #         file_url = os.path.join('img', company_name, filename)  # Store relative path

    #         # Extract features
    #         feature_data = extract_features(fs.path(filename))

    #         # Save image details
    #         Image.objects.create(
    #             company_name=company_name,
    #             image=file_url,
    #             image_id=image_id,
    #             pattern_features=feature_data["pattern"],
    #             color_features=feature_data["color"]
    #         )

    #     return redirect('upload_image')

    # return render(request, "cbir_app/upload_image.html")

@csrf_exempt
def upload_image(request):
    if request.method == "POST" and request.FILES.getlist('images'):
        company_name = request.POST.get("company_name", "").strip()
        if not company_name:
            return render(request, "cbir_app/upload_image.html", {"error": "Company name is required."})
        
        image_id = request.POST.get("image_id")

        for image_file in request.FILES.getlist('images'):
            # Create a temporary file to save the image
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image_file.read())  # Write the uploaded file data
                temp_file_path = temp_file.name  # Get the file path

            try:
                # Extract features from the saved image file
                feature_data = extract_features(temp_file_path)

                # Save only features & metadata (no actual image)
                Image.objects.create(
                    company_name=company_name,
                    image_id=image_id,
                    pattern_features=feature_data["pattern"],
                    color_features=feature_data["color"]
                )
            finally:
                # Remove the temporary file
                os.remove(temp_file_path)

        return redirect('upload_image')

    return render(request, "cbir_app/upload_image.html")



# @csrf_exempt
# def search_image(request):
#     if request.method == "POST":
#         query_image_file = request.FILES['image']
#         fs = FileSystemStorage()
#         file_path = fs.save(query_image_file.name, query_image_file)
#         query_image_url = fs.url(file_path)

#         # Extract features from the query image
#         query_features = extract_features(fs.path(file_path))

#         images = Image.objects.all()

#         # Fetch all stored images and their features
#         database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

#         # Find similar images
#         similarities = find_similar_images(query_features, database_features, top_k=5)

#         pattern_results = [
#             {
#                 "image": images[int(idx)].image.url,  # Get image URL
#                 "company_name": images[int(idx)].company_name,  # Get company name
#                 "score": similarities["pattern"]["scores"][i],
#                 "image_id":images[int(idx)].image_id
#             }
#             for i, idx in enumerate(similarities["pattern"]["indices"])
#         ]

#         color_results = [
#             {
#                 "image": images[int(idx)].image.url,
#                 "company_name": images[int(idx)].company_name,
#                 "score": similarities["color"]["scores"][i],
#                 "image_id":images[int(idx)].image_id
#             }
#             for i, idx in enumerate(similarities["color"]["indices"])
#         ]

#         return render(request, 'cbir_app/search_results.html', {
#             'query_image_url': query_image_url,
#             'pattern_results': pattern_results,
#             'color_results': color_results,
#         })

#     return render(request, 'cbir_app/search_image.html')

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


