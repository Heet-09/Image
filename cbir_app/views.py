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

@csrf_exempt
# def upload_image(request):
#     if request.method == "POST" and request.FILES.getlist('images'):
#         # Get list of uploaded files
#         image_files = request.FILES.getlist('images')
#         fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'img'))

#         for image_file in image_files:
#             filename = fs.save(image_file.name, image_file)

#             # Generate the correct file URL
#             file_url = os.path.join('img', filename)  # Relative path under 'MEDIA_URL'

#             # Extract features for pattern and color
#             feature_data = extract_features(fs.path(filename))

#             # Save the image and its features
#             Image.objects.create(
#                 image=file_url,
#                 pattern_features=feature_data["pattern"],
#                 color_features=feature_data["color"]
#             )

#         return redirect('upload_image')  # Redirect back to the upload page

#     return render(request, 'cbir_app/upload_image.html')
def upload_image(request):
    if request.method == "POST" and request.FILES.getlist('images'):
        company_name = request.POST.get("company_name").strip()
        if not company_name:
            return render(request, "cbir_app/upload_image.html", {"error": "Company name is required."})

        # Define folder path based on company name
        company_folder = os.path.join(settings.MEDIA_ROOT, 'img', company_name)
        os.makedirs(company_folder, exist_ok=True)

        fs = FileSystemStorage(location=company_folder)

        for image_file in request.FILES.getlist('images'):
            filename = fs.save(image_file.name, image_file)
            file_url = os.path.join('img', company_name, filename)  # Store relative path

            # Extract features
            feature_data = extract_features(fs.path(filename))

            # Save image details
            Image.objects.create(
                company_name=company_name,
                image=file_url,
                pattern_features=feature_data["pattern"],
                color_features=feature_data["color"]
            )

        return redirect('upload_image')

    return render(request, "cbir_app/upload_image.html")

@csrf_exempt
def search_image(request):
    if request.method == "POST":
        query_image_file = request.FILES['image']
        fs = FileSystemStorage()
        file_path = fs.save(query_image_file.name, query_image_file)
        query_image_url = fs.url(file_path)

        # Extract features from the query image
        query_features = extract_features(fs.path(file_path))

        # Fetch all stored images and their features
        images = Image.objects.all()
        database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

        # Find similar images
        similarities = find_similar_images(query_features, database_features, top_k=5)

        pattern_results = [
            {
                "image": images[int(idx)].image.url,  # Get image URL
                "company_name": images[int(idx)].company_name,  # Get company name
                "score": similarities["pattern"]["scores"][i]
            }
            for i, idx in enumerate(similarities["pattern"]["indices"])
        ]

        color_results = [
            {
                "image": images[int(idx)].image.url,
                "company_name": images[int(idx)].company_name,
                "score": similarities["color"]["scores"][i]
            }
            for i, idx in enumerate(similarities["color"]["indices"])
        ]

        return render(request, 'cbir_app/search_results.html', {
            'query_image_url': query_image_url,
            'pattern_results': pattern_results,
            'color_results': color_results,
        })

    return render(request, 'cbir_app/search_image.html')


# @csrf_exempt
# def search_image(request):
#     if request.method == "POST":
#         if 'image' not in request.FILES:
#             return JsonResponse({"error": "No image file uploaded"}, status=400)

#         query_image_file = request.FILES['image']
#         fs = FileSystemStorage()
#         file_path = fs.save(query_image_file.name, query_image_file)
#         query_image_url = fs.url(file_path)

#         # Extract features from the query image
#         query_features = extract_features(fs.path(file_path))

#         # Fetch all stored images and their features
#         images = Image.objects.all()
#         database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

#         # Find similar images
#         similarities = find_similar_images(query_features, database_features, top_k=5)

#         pattern_results = [
#             {
#                 "image": request.build_absolute_uri(images[int(idx)].image.url),  # Full URL of image
#                 "company_name": images[int(idx)].company_name,
#                 "score": similarities["pattern"]["scores"][i]
#             }
#             for i, idx in enumerate(similarities["pattern"]["indices"])
#         ]

#         color_results = [
#             {
#                 "image": request.build_absolute_uri(images[int(idx)].image.url),
#                 "company_name": images[int(idx)].company_name,
#                 "score": similarities["color"]["scores"][i]
#             }
#             for i, idx in enumerate(similarities["color"]["indices"])
#         ]

#         return JsonResponse({
#             "query_image": request.build_absolute_uri(query_image_url),
#             "pattern_results": pattern_results,
#             "color_results": color_results
#         }, status=200)

#     return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)

