# cbir_app/views.py
from django.shortcuts import render, redirect
from .models import Image
from .utils import extract_features, find_similar_images
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

# def upload_image(request):
#     if request.method == "POST" and request.FILES['image']:
#         image_file = request.FILES['image']
#         fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'img'))
#         filename = fs.save(image_file.name, image_file)

#         # Generate the correct file URL
#         file_url = os.path.join('img', filename)  # Relative path under 'MEDIA_URL'

#         # Save the image and features
#         feature_array = extract_features(fs.path(filename))
#         Image.objects.create(image=file_url, features=feature_array)

#         return redirect('upload_image')
#     return render(request, 'cbir_app/upload_image.html')


def upload_image(request):
    if request.method == "POST" and request.FILES.getlist('images'):
        # Get list of uploaded files
        image_files = request.FILES.getlist('images')
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'img'))

        for image_file in image_files:
            filename = fs.save(image_file.name, image_file)

            # Generate the correct file URL
            file_url = os.path.join('img', filename)  # Relative path under 'MEDIA_URL'

            # Extract features for pattern and color
            feature_data = extract_features(fs.path(filename))

            # Save the image and its features
            Image.objects.create(
                image=file_url,
                pattern_features=feature_data["pattern"],
                color_features=feature_data["color"]
            )

        return redirect('upload_image')  # Redirect back to the upload page

    return render(request, 'cbir_app/upload_image.html')


def search_image(request):
    if request.method == "POST":
        query_image_file = request.FILES['image']
        fs = FileSystemStorage()
        file_path = fs.save(query_image_file.name, query_image_file)
        query_image_url = fs.url(file_path)

        # Extract features from query image
        query_features = extract_features(fs.path(file_path))

        # Fetch all stored images and their features
        images = Image.objects.all()
        database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

        # Find similar images
        similarities = find_similar_images(query_features, database_features, top_k=5)

        pattern_results = [
            {"image": images[int(idx)], "score": similarities["pattern"]["scores"][i]}
            for i, idx in enumerate(similarities["pattern"]["indices"])
        ]

        # for pat in pattern_results:
        #     print(f"Image: {pat['image']},pat['']")

        color_results = [
            {"image": images[int(idx)], "score": similarities["color"]["scores"][i]}
            for i, idx in enumerate(similarities["color"]["indices"])
        ]


        return render(request, 'cbir_app/search_results.html', {
            'query_image_url': query_image_url,
            'pattern_results': pattern_results,
            'color_results': color_results,
        })

    return render(request, 'cbir_app/search_image.html')
