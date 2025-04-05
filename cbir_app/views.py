# C:\code\Kreon\image\cbir_app\views.py
# cbir_app/views.py
from django.shortcuts import render, redirect
from .models import Image,ImageFeature
from .utils import extract_features, find_similar_images
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse
import os
import tempfile


def home(request):
    return render (request, "cbir_app/home.html")
# Dummy Token
DUMMY_TOKEN = "my-secret-dummy-token"

def validate_token(request):
    """
    Helper function to validate the authorization token.
    """
    token = request.headers.get("Authorization")
    if token != f"Token {DUMMY_TOKEN}":
        return Response({"error": "Invalid or missing token"}, status=status.HTTP_401_UNAUTHORIZED)
    return None

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

@api_view(['POST'])
# @parser_classes([MultiPartParser, FormParser])
def upload_image_api(request):
    token_response = validate_token(request)
    if token_response:
        return token_response

    if 'images' not in request.FILES:
        return Response({"error": "No images provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    company_name = request.data.get("company_name", "").strip()
    if not company_name:
        return Response({"error": "Company name is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    company_folder = os.path.join(settings.MEDIA_ROOT, 'img', company_name)
    os.makedirs(company_folder, exist_ok=True)
    fs = FileSystemStorage(location=company_folder)
    
    uploaded_images = []
    for image_file in request.FILES.getlist('images'):
        filename = fs.save(image_file.name, image_file)
        file_url = os.path.join('img', company_name, filename)
        
        feature_data = extract_features(fs.path(filename))
        
        image_record = Image.objects.create(
            company_name=company_name,
            image=file_url,
            pattern_features=feature_data["pattern"],
            color_features=feature_data["color"]
        )
        
        uploaded_images.append({"id": image_record.id, "image_url": file_url})
    
    return Response({"message": "Images uploaded successfully", "uploaded_images": uploaded_images}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
# @parser_classes([MultiPartParser])
def search_image_api(request):
    token_response = validate_token(request)
    if token_response:
        return token_response

    if 'image' not in request.FILES:
        return Response({"error": "No query image provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    query_image_file = request.FILES['image']
    fs = FileSystemStorage()
    file_path = fs.save(query_image_file.name, query_image_file)
    query_image_url = fs.url(file_path)
    
    query_features = extract_features(fs.path(file_path))
    
    images = Image.objects.all()
    database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]
    
    similarities = find_similar_images(query_features, database_features, top_k=5)
    
    pattern_results = [{
        "image": images[int(idx)].image.url,
        "company_name": images[int(idx)].company_name,
        "score": similarities["pattern"]["scores"][i]
    } for i, idx in enumerate(similarities["pattern"]["indices"])]
    
    color_results = [{
        "image": images[int(idx)].image.url,
        "company_name": images[int(idx)].company_name,
        "score": similarities["color"]["scores"][i]
    } for i, idx in enumerate(similarities["color"]["indices"])]
    
    return Response({
        "query_image_url": query_image_url,
        "pattern_results": pattern_results,
        "color_results": color_results
    }, status=status.HTTP_200_OK)



# ################### for id ####################
###################################################
#############################################








#################################
def upload_image_id(request):
    """
    View to upload an image, extract features, and store metadata in the database.
    """
    if request.method == "POST":
        # Validate token

        if "images" not in request.FILES:
            return render(request, "cbir_app/upload_image_id.html", {"error": "No images provided"})

        company_name = request.POST.get("company_name", "").strip()
        if not company_name:
            return render(request, "cbir_app/upload_image_id.html", {"error": "Company name is required."})

        image_id = request.POST.get("image_id")
        uploaded_images = []

        for image_file in request.FILES.getlist("images"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image_file.read())  
                temp_file_path = temp_file.name  

            try:
                # Extract features
                feature_data = extract_features(temp_file_path)

                # Save metadata (without storing the actual image)
                image_entry = ImageFeature.objects.create(
                    company_name=company_name,
                    image_id=image_id,
                    pattern_features=feature_data["pattern"],
                    color_features=feature_data["color"]
                )
                uploaded_images.append({
                    "image_id": image_entry.image_id,
                    "company_name": image_entry.company_name
                })
            finally:
                os.remove(temp_file_path)

        return render(request, "cbir_app/upload_image_id.html", {"message": "Images uploaded successfully", "uploaded_images": uploaded_images})

    return render(request,"cbir_app/upload_image_id.html")

def search_image_id(request):
    """
    View to search for similar images based on features and render results.
    """
    if request.method == "POST":
    
        if "image" not in request.FILES:
            return render(request, "cbir_app/search_image_id.html", {"error": "No image provided"})

        query_image_file = request.FILES["image"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(query_image_file.read())  
            temp_file_path = temp_file.name  

        try:
            query_features = extract_features(temp_file_path)

            images = ImageFeature.objects.all()
            database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

            if not database_features:
                return render(request, "cbir_app/search_image_id.html", {"message": "No images in database", "pattern_results": [], "color_results": []})

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

            return render(request, "cbir_app/search_results_id.html", {
                "message": "Search completed",
                "pattern_results": pattern_results,
                "color_results": color_results,
            })

        finally:
            os.remove(temp_file_path)
    
    return render(request, "cbir_app/search_image_id.html")


@api_view(["POST"])
def upload_image_id_api(request):
    """
    API to upload an image, extract features, and store in the database.
    """
    # Validate token
    token_response = validate_token(request)
    if token_response:
        return token_response

    if "images" not in request.FILES:
        return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)

    company_name = request.data.get("company_name", "").strip()
    if not company_name:
        return Response({"error": "Company name is required."}, status=status.HTTP_400_BAD_REQUEST)

    image_id = request.data.get("image_id")

    uploaded_images = []
    for image_file in request.FILES.getlist("images"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(image_file.read())  
            temp_file_path = temp_file.name  

        try:
            # Extract features
            feature_data = extract_features(temp_file_path)

            # Save metadata (without storing the actual image)
            image_entry = ImageFeature.objects.create(
                company_name=company_name,
                image_id=image_id,
                pattern_features=feature_data["pattern"],
                color_features=feature_data["color"]
            )
            uploaded_images.append({
                "image_id": image_entry.image_id,
                "company_name": image_entry.company_name
            })
        finally:
            os.remove(temp_file_path)

    return Response({"message": "Images uploaded successfully", "uploaded_images": uploaded_images}, status=status.HTTP_201_CREATED)

@api_view(["POST"])
def search_image_id_api(request):
    """
    API to search for similar images based on features.
    """
    # Validate token
    token_response = validate_token(request)
    if token_response:
        return token_response

    if "image" not in request.FILES:
        return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

    query_image_file = request.FILES["image"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_file.write(query_image_file.read())  
        temp_file_path = temp_file.name  

    try:
        query_features = extract_features(temp_file_path)

        images = ImageFeature.objects.all()
        database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

        if not database_features:
            return Response({"message": "No images in database", "pattern_results": [], "color_results": []})

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

        return Response({
            "message": "Search completed",
            "pattern_results": pattern_results,
            "color_results": color_results,
        }, status=status.HTTP_200_OK)

    finally:
        os.remove(temp_file_path)


