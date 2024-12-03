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

            # Save the image and its features
            feature_array = extract_features(fs.path(filename))
            Image.objects.create(image=file_url, features=feature_array)

        return redirect('upload_image')  # Redirect back to the upload page

    return render(request, 'cbir_app/upload_image.html')

import numpy as np
# def search_image(request):
#     if request.method == "POST":
#         query_image_file = request.FILES['image']
#         fs = FileSystemStorage()
#         file_path = fs.save(query_image_file.name, query_image_file)

#         # Extract features from query image
#         query_features = extract_features(fs.path(file_path))

#         # Fetch all stored images and their features
#         images = Image.objects.all()
#         database_features = [np.array(img.features) for img in images]
#         print("database_features",database_features)

#         # Find similar images
#         indices = find_similar_images(query_features, database_features)
#         print("indices",indices)

#         # Ensure indices are integers (convert them to Python int)
#         indices = [int(i) for i in indices]
#         print("idics",indices)

#         # Get the similar images using integer indices
#         similar_images = [images[i] for i in indices]
#         print("similar images",similar_images)

#         return render(request, 'cbir_app/search_results.html', {'images': similar_images})
#     return render(request, 'cbir_app/search_image.html')

# # for the priting the similarity scores 
# def search_image(request):
#     if request.method == "POST":
#         query_image_file = request.FILES['image']
#         fs = FileSystemStorage()
#         file_path = fs.save(query_image_file.name, query_image_file)

#         # Extract features from query image
#         query_features = extract_features(fs.path(file_path))

#         # Fetch all stored images and their features
#         images = Image.objects.all()
#         database_features = [np.array(img.features) for img in images]

#         # Find similar images and their scores
#         indices, similarity_scores = find_similar_images(query_features, database_features)
#         print("Indices:", indices)
#         print("Similarity Scores:", similarity_scores)

#         # Get the similar images with their scores
#         similar_images_with_scores = [
#             {"image": images[i], "score": similarity_scores[idx]}
#             for idx, i in enumerate(indices)
#         ]
#         print("Similar Images with Scores:", similar_images_with_scores)

#         return render(request, 'cbir_app/search_results.html', {'similar_images': similar_images_with_scores})

#     return render(request, 'cbir_app/search_image.html')

def search_image(request):
    if request.method == "POST":
        query_image_file = request.FILES['image']
        fs = FileSystemStorage()
        file_path = fs.save(query_image_file.name, query_image_file)
        query_image_url = fs.url(file_path)  # Get the URL of the uploaded query image

        # Extract features from query image
        query_features = extract_features(fs.path(file_path))

        # Fetch all stored images and their features
        images = Image.objects.all()
        database_features = [np.array(img.features) for img in images]

        # Find similar images and their scores
        indices, similarity_scores = find_similar_images(query_features, database_features)
        indices = [int(i) for i in indices]  # Ensure indices are Python integers

        # Get the similar images with their scores
        similar_images_with_scores = [
            {"image": images[i], "score": similarity_scores[idx]}
            for idx, i in enumerate(indices)
        ]

        return render(request, 'cbir_app/search_results.html', {
            'query_image_url': query_image_url,  # Pass the query image URL to the template
            'similar_images': similar_images_with_scores,
        })

    return render(request, 'cbir_app/search_image.html')
