
# C:\code\Kreon\image\cbir_app\views.py
# cbir_app/views.py
from django.db import IntegrityError
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
from pathlib import Path
# from .faiss_index_loader import pattern_index, color_index, image_list
import time
from .feature_cache import feature_cache



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

@api_view(["POST"])
def search_image_id_api_new(request):
    if "image" not in request.FILES:
        return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_file.write(request.FILES["image"].read())
        temp_file_path = temp_file.name

    try:
        query_features = extract_features(temp_file_path)
        os.remove(temp_file_path)  # Clean up file

        query_pattern = np.array(query_features["pattern"]).astype("float32")
        query_color = np.array(query_features["color"]).astype("float32")

        faiss.normalize_L2(query_pattern.reshape(1, -1))
        faiss.normalize_L2(query_color.reshape(1, -1))

        top_k = int(request.data.get("top_k", 5))
        pattern_scores, pattern_indices = pattern_index.search(query_pattern.reshape(1, -1), top_k)
        color_scores, color_indices = color_index.search(query_color.reshape(1, -1), top_k)

        def format_results(indices, scores):
            results = []
            for i, idx in enumerate(indices[0]):
                image_data = image_list[idx]
                results.append({
                    "image_ref_id": image_data["image_ref_id"],
                    "company_id": image_data["company_id"],
                    "score": float(scores[0][i])
                })
            return results

        return Response({
            "message": "Search completed.",
            "pattern_results": format_results(pattern_indices, pattern_scores),
            "color_results": format_results(color_indices, color_scores)
        })

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def upload_image(request):
    if request.method == "POST" and request.FILES.getlist('images'):
        try:
            company_id = int(request.POST.get("company_id").strip())
        except (TypeError, ValueError):
            return render(request, "cbir_app/upload_image.html", {"error": "Valid company ID is required."})
        
        filters = {}
        for i in range(1, 11):
            filters[f'filter_{i}'] = request.POST.get(f'filter_{i}', '').strip()

        # Define folder path based on company name
        company_folder = os.path.join(settings.MEDIA_ROOT, 'img', str(company_id))
        os.makedirs(company_folder, exist_ok=True)

        fs = FileSystemStorage(location=company_folder)

        for image_file in request.FILES.getlist('images'):
            filename = fs.save(image_file.name, image_file)
            file_url = os.path.join('img', str(company_id), filename)# Store relative path

            # Extract features
            feature_data = extract_features(fs.path(filename))

            # Save image details
            Image.objects.create(
                company_id=company_id,
                image=file_url,
                pattern_features=feature_data["pattern"],
                color_features=feature_data["color"],
                **filters
            )

        return redirect('upload_image')
    context = {
        'range_10': range(1, 11)
    }
    return render(request, 'cbir_app/upload_image.html', context)

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
                "company_id": images[int(idx)].company_id,  # Get company name
                "score": similarities["pattern"]["scores"][i]
            }
            for i, idx in enumerate(similarities["pattern"]["indices"])
        ]

        color_results = [
            {
                "image": images[int(idx)].image.url,
                "company_id": images[int(idx)].company_id,
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
def upload_image_api(request):
    token_response = validate_token(request)
    if token_response:
        return token_response

    if 'images' not in request.FILES:
        return Response({"error": "No images provided."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        company_id = int(request.data.get("company_id", "").strip())
    except (TypeError, ValueError):
        return Response({"error": "Valid company ID is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    filters = {}
    for i in range(1, 11):
        filters[f'filter_{i}'] = request.data.get(f'filter_{i}', '').strip()

    company_folder = os.path.join(settings.MEDIA_ROOT, 'img', str(company_id))
    os.makedirs(company_folder, exist_ok=True)
    fs = FileSystemStorage(location=company_folder)

    uploaded_images = []
    for image_file in request.FILES.getlist('images'):
        filename = fs.save(image_file.name, image_file)
        file_url = os.path.join('img', str(company_id), filename)

        feature_data = extract_features(fs.path(filename))

        image_record = Image.objects.create(
            company_id=company_id,
            image=file_url,
            pattern_features=feature_data["pattern"],
            color_features=feature_data["color"],
            **filters
        )

        uploaded_images.append({"id": image_record.id, "image_url": file_url})

    return Response({
        "message": "Images uploaded successfully",
        "uploaded_images": uploaded_images
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def search_image_api(request):
    token_response = validate_token(request)
    if token_response:
        return token_response

    if 'image' not in request.FILES:
        return Response({"error": "No query image provided."}, status=status.HTTP_400_BAD_REQUEST)

    # Get optional parameters
    top_k = int(request.data.get("top_k", 5))  # default to 5
    threshold = float(request.data.get("threshold", 0.0))  # default to 0.0

    # Save uploaded image
    query_image_file = request.FILES['image']
    fs = FileSystemStorage()
    file_path = fs.save(query_image_file.name, query_image_file)
    query_image_url = fs.url(file_path)

    # Extract features
    query_features = extract_features(fs.path(file_path))

    # Get all images and their features
    images = list(Image.objects.all())
    database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

    # Compute similarities
    similarities = find_similar_images(query_features, database_features)

    # Filter results by threshold and limit by top_k
    pattern_results = filter_and_format_results(similarities["pattern"], images, threshold, top_k)
    color_results = filter_and_format_results(similarities["color"], images, threshold, top_k)

    return Response({
        "query_image_url": query_image_url,
        "pattern_results": pattern_results,
        "color_results": color_results
    }, status=status.HTTP_200_OK)

def filter_and_format_results(similarity_data, images, threshold, top_k):
    results = []
    count = 0
    for i, idx in enumerate(similarity_data["indices"]):
        score = similarity_data["scores"][i]
        if score >= threshold:
            results.append({
                "image": images[int(idx)].image.url,
                "company_id": images[int(idx)].company_id,
                "score": score
            })
            count += 1
        if count >= top_k:
            break
    return results
# ################### for id ####################
###################################################
#############################################


def upload_image_id(request):
    """
    View to upload an image, extract features, and store metadata in the database.
    """
    if request.method == "POST":
        # Validate token

        if "images" not in request.FILES:
            return render(request, "cbir_app/upload_image_id.html", {"error": "No images provided"})

        try:
            company_id = int(request.POST.get("company_id", ""))
        except ValueError:
            return render(request, "cbir_app/upload_image_id.html", {"error": "Valid company ID is required."})
        
        filters = {}
        for i in range(1, 11):
            filters[f'filter_{i}'] = request.POST.get(f'filter_{i}', '').strip()

        image_ref_id = request.POST.get("image_ref_id")
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
                    company_id=company_id,
                    image_ref_id=image_ref_id,
                    pattern_features=feature_data["pattern"],
                    color_features=feature_data["color"],
                    **filters
                )
                uploaded_images.append({
                    "image_ref_id": image_entry.image_ref_id,
                    "company_id": image_entry.company_id
                })
            finally:
                os.remove(temp_file_path)

        return render(request, "cbir_app/upload_image_id.html", {"message": "Images uploaded successfully", "uploaded_images": uploaded_images})

    context = {
        'range_10': range(1, 11)
    }
    return render(request,"cbir_app/upload_image_id.html",context)

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
                    "company_id": images[int(idx)].company_id,
                    "score": similarities["pattern"]["scores"][i],
                    "image_ref_id": images[int(idx)].image_ref_id,
                }
                for i, idx in enumerate(similarities["pattern"]["indices"])
            ]

            color_results = [
                {
                    "company_id": images[int(idx)].company_id,
                    "score": similarities["color"]["scores"][i],
                    "image_ref_id": images[int(idx)].image_ref_id,
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

    try:
        company_id = int(request.POST.get("company_id", ""))
    except ValueError:
        return render(request, "cbir_app/upload_image_id.html", {"error": "Valid company ID is required."})
        
    image_ref_id = request.data.get("image_ref_id")

    filters = {}
    for i in range(1, 11):
        filters[f'filter_{i}'] = request.data.get(f'filter_{i}', '').strip()

    if ImageFeature.objects.filter(company_id=company_id, image_ref_id=image_ref_id).exists():
        print("Image reference ID already exists")
        return render(request, "cbir_app/upload_image_id.html", {
            "error": "This company ID and image reference ID combination already exists."
        })

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
                company_id=company_id,
                image_ref_id=image_ref_id,
                pattern_features=feature_data["pattern"],
                color_features=feature_data["color"],
                **filters
            )
            uploaded_images.append({
                "image_ref_id": image_entry.image_ref_id,
                "company_id": image_entry.company_id
            })
        except IntegrityError:
            return render(request, "cbir_app/upload_image_id.html", {
                "error": "This company ID and image reference ID combination already exists (enforced at database level)."
            })
        finally:
            os.remove(temp_file_path)

    return Response({"message": "Images uploaded successfully", "uploaded_images": uploaded_images}, status=status.HTTP_201_CREATED)
# @csrf_exempt
# @api_view(["POST"])
# def search_image_id_api(request):
#     """
#     API to search for similar images based on features.
#     """
#     # Validate token
#     start_time = time.time()
#     token_response = validate_token(request)
#     if token_response:
#         return token_response

#     if "image" not in request.FILES:
#         return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
    
#     top_k = int(request.data.get("top_k", 50))
#     p_threshold = float(request.data.get("p_threshold", 0.0))
#     c_threshold = float(request.data.get("c_threshold", 0.0))
#     pattern_threshold = p_threshold / 100
#     color_threshold = c_threshold / 100
#     print(pattern_threshold,p_threshold,color_threshold,c_threshold)
#     # Get company_id filter
#     print("top_k",top_k)
#     company_id = request.data.get("company_id")
#     if not company_id:
#         return Response({"error": "Missing company_id"}, status=status.HTTP_400_BAD_REQUEST)

#     # Build filter kwargs
#     filters = {"company_id": company_id}
#     float_filters = {"filter_1", "filter_2", "filter_4"}  # filters that store float-like strings
#     for i in range(1, 11):
#         key = f"filter_{i}"
#         value = request.data.get(key)
#         if value not in [None, "", "null"]:
#             if key in float_filters:
#                 try:
#                     filters[key] = str(float(value))  # normalize to '7.0'
#                 except ValueError:
#                     filters[key] = str(value)
#             else:
#                 filters[key] = str(value)  # leave as-is for filters like '26'

#     print("Filters used in query:", filters)

#     # Get uploaded image
#     query_image_file = request.FILES["image"]
#     original_extension = os.path.splitext(query_image_file.name)[-1].lower()

#     valid_extensions = {'.jpg', '.jpeg', '.png'}
#     if original_extension not in valid_extensions:
#         return Response({"error": "Unsupported file type. Use jpg, jpeg, or png."}, status=status.HTTP_400_BAD_REQUEST)
    
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg,.jpeg,.png") as temp_file:
#         temp_file.write(query_image_file.read())
#         temp_file_path = temp_file.name

#     try:
# 	        # Extract features
#         t1 = time.time()
#         query_features = extract_features(temp_file_path)
#         t2 = time.time()
#         print(f"Feature extraction time: {t2 - t1:.3f} seconds")
#         # check time for this line 
#         t3 = time.time()
#         images = feature_cache.images

#         t4 = time.time()
#         print(f"Database fetch time: {t4 - t3:.3f} seconds")

#         database_features = [
#             {"pattern": img["pattern_features"], "color": img["color_features"]}
#             for img in images
#         ]

#         if not database_features:
#             return Response({
#                 "message": "No images in database matching the filters.",
#                 "pattern_results": [],
#                 "color_results": []
#             }, status=status.HTTP_200_OK)

#         # Find similarities
#         t5 = time.time()
#         similarities = find_similar_images(query_features, database_features,top_k)
#         t6 = time.time()
#         print(f"Similarity search time: {t6 - t5:.3f} seconds")
#         print("before function cal l")
#         # Filter and format results
#         t7 = time.time()
#         pattern_results = filter_and_format_image_id_results(similarities["pattern"], images, pattern_threshold, top_k)
#         t8 = time.time()
#         print(f"Pattern filtering time: {t8 - t7:.3f} seconds")
#         t9 = time.time()
#         color_results = filter_and_format_image_id_results(similarities["color"], images, color_threshold, top_k)
#         t10 = time.time()
#         print(f"Color filtering time: {t10 - t9:.3f} seconds")
#         print("After function call")
#         total_time = time.time() - start_time
#         print(f"Total API execution time: {total_time:.3f} seconds")
#         return Response({
#             "message": "Search completed.",
#             "pattern_results": pattern_results,
#             "color_results": color_results
#         }, status=status.HTTP_200_OK)
    
#         response["Access-Control-Allow-Origin"] = "*"
#         response["Access-Control-Allow-Methods"] = "POST, OPTIONS"

#     finally:
#         os.remove(temp_file_path)


@csrf_exempt
@api_view(["POST"])
def search_image_id_api(request):
    """
    API to search for similar images based on features.
    Uses in-memory FAISS index and cached features for speed.
    """
    import numpy as np
    import faiss
    import os
    import time

    # Validate token
    start_time = time.time()
    token_response = validate_token(request)
    if token_response:
        return token_response

    if "image" not in request.FILES:
        return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
    
    top_k = int(request.data.get("top_k", 50))
    p_threshold = float(request.data.get("p_threshold", 0.0))
    c_threshold = float(request.data.get("c_threshold", 0.0))
    pattern_threshold = p_threshold / 100
    color_threshold = c_threshold / 100

    company_id = request.data.get("company_id")
    if not company_id:
        return Response({"error": "Missing company_id"}, status=status.HTTP_400_BAD_REQUEST)

    # Get uploaded image
    query_image_file = request.FILES["image"]
    original_extension = os.path.splitext(query_image_file.name)[-1].lower()
    valid_extensions = {'.jpg', '.jpeg', '.png'}
    if original_extension not in valid_extensions:
        return Response({"error": "Unsupported file type. Use jpg, jpeg, or png."}, status=status.HTTP_400_BAD_REQUEST)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=original_extension) as temp_file:
        temp_file.write(query_image_file.read())
        temp_file_path = temp_file.name

    try:
        t1 = time.time()
        query_features = extract_features(temp_file_path)
        t2 = time.time()
        print(f"Feature extraction time: {t2 - t1:.3f} seconds")

        # Prepare query vectors
        query_pattern = np.array(query_features["pattern"]).astype("float32")
        query_color = np.array(query_features["color"]).astype("float32")
        faiss.normalize_L2(query_pattern.reshape(1, -1))
        faiss.normalize_L2(query_color.reshape(1, -1))

        # Use cached features and FAISS indices
        images = feature_cache.images
        pattern_index = feature_cache.pattern_index
        color_index = feature_cache.color_index

        if len(images) == 0:
            return Response({
                "message": "No images in database matching the filters.",
                "pattern_results": [],
                "color_results": []
            }, status=status.HTTP_200_OK)

        # Similarity search
        t3 = time.time()
        pattern_scores, pattern_indices = pattern_index.search(query_pattern.reshape(1, -1), top_k)
        color_scores, color_indices = color_index.search(query_color.reshape(1, -1), top_k)
        t4 = time.time()
        print(f"FAISS similarity search time: {t4 - t3:.3f} seconds")

        # Format results
        def format_results(indices, scores, threshold):
            results = []
            count = 0
            for i, idx in enumerate(indices[0]):
                score = float(scores[0][i])
                if score >= threshold:
                    img = images[int(idx)]
                    results.append({
                        "image_ref_id": img.image_ref_id,
                        "company_id": img.company_id,
                        "score": score
                    })
                    count += 1
                if count >= top_k:
                    break
            return results

        pattern_results = format_results(pattern_indices, pattern_scores, pattern_threshold)
        color_results = format_results(color_indices, color_scores, color_threshold)

        total_time = time.time() - start_time
        print(f"Total API execution time: {total_time:.3f} seconds")
        return Response({
            "message": "Search completed.",
            "pattern_results": pattern_results,
            "color_results": color_results
        }, status=status.HTTP_200_OK)

    finally:
        os.remove(temp_file_path)


def filter_and_format_image_id_results(similarity_data, images, threshold, top_k):
    print(threshold)
    print("hello")
    print(top_k,"top_K")
    results = []
    count = 0
    for i, idx in enumerate(similarity_data["indices"]):
        score = similarity_data["scores"][i]
        if score >= threshold:
            results.append({
                "image_ref_id": images[int(idx)]["image_ref_id"],
                "company_id": images[int(idx)]["company_id"],
                "score": score
            })
            count += 1
        if count >= top_k:
            break
    return results




################Upload Image API######################
def upload_assets(request):
    if request.method == "POST":
        excel_file = request.FILES.get("excel_file")
        image_files = request.FILES.getlist("images")

        if not excel_file or not image_files:
            return render(request, "cbir_app/upload_assets.html", {"error": "Both Excel and images are required."})

        data_dir = Path(settings.BASE_DIR) / "data"
        images_dir = data_dir / "images"

        # Ensure directories exist
        data_dir.mkdir(exist_ok=True)
        images_dir.mkdir(exist_ok=True)

        # Save Excel
        excel_path = data_dir / "image_data.xlsx"
        with open(excel_path, "wb+") as f:
            for chunk in excel_file.chunks():
                f.write(chunk)

        # Save images
        for image in image_files:
            image_path = images_dir / image.name
            with open(image_path, "wb+") as f:
                for chunk in image.chunks():
                    f.write(chunk)

        return render(request, "cbir_app/upload_assets.html", {"message": "Files uploaded successfully."})

    return render(request, "cbir_app/upload_assets.html")

