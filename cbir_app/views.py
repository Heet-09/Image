from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from .models import Image
from .utils import extract_features, find_similar_images
import os
import tempfile

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

@api_view(["POST"])
def upload_image(request):
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
            image_entry = Image.objects.create(
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
def search_image(request):
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

        images = Image.objects.all()
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
