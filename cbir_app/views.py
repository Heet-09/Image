
# C:\code\Kreon\image\cbir_app\views.py
# cbir_app/views.py
from django.db import IntegrityError
from django.shortcuts import render, redirect
from .models import Image,ImageFeature
# from .utils import extract_features, find_similar_images
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse
from django.db.utils import OperationalError
from django.db import connection
import os
import tempfile
from pathlib import Path
# from .faiss_index_loader import pattern_index, color_index, image_list
import time
# Pre-load feature cache at module import
from .feature_cache import feature_cache
# feature_cache.load()  # Load once at startu/p
# # from .utils import extract_features, find_similar_images_with_chi_square, find_similar_images_weighted
# from .utils import extract_features, find_similar_images_safe
from .utils import *

try:
    # Only try loading if table exists
    if 'cbir_app_imagefeature' in connection.introspection.table_names():
        feature_cache.load()
except OperationalError:
    # Tables are not ready yet (migrate not run)
    pass



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


def combine_pattern_color(similarities, images, top_k):
    # Map index to score for both pattern and color
    pattern_dict = {int(idx): float(similarities["pattern"]["scores"][i]) for i, idx in enumerate(similarities["pattern"]["indices"])}
    color_dict = {int(idx): float(similarities["color"]["scores"][i]) for i, idx in enumerate(similarities["color"]["indices"])}
    combined = []
    all_indices = set(pattern_dict.keys()) | set(color_dict.keys())
    for idx in all_indices:
        pattern_score = pattern_dict.get(idx, 0)
        color_score = color_dict.get(idx, 0)
        combined_score = (pattern_score + color_score) / 2
        img = images[int(idx)]
        # For ImageFeature model, use .image_ref_id; for Image model, use .id or .image_id
        combined.append({
            "image": getattr(img, "image", None).url if hasattr(img, "image") else None,
            "image_ref_id": getattr(img, "image_ref_id", None),
            "company_id": img.company_id,
            "combined_score": combined_score
        })
    # Sort by combined_score descending and take top_k
    combined = sorted(combined, key=lambda x: x["combined_score"], reverse=True)[:top_k]
    return combined

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


############################### FOR IMAGE #################################

########### WEB PAGE ##################

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
            file_url = os.path.join('img', str(company_id), filename)  # Store relative path
            
            # Extract features using ENHANCED method
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
        
        # Extract features using ENHANCED method
        query_features = extract_features(fs.path(file_path))
        images = list(Image.objects.all())
        database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]
        
        # Use the SAFE method that handles dimension mismatches
        similarities = find_similar_images_safe(query_features, database_features, top_k=5)
        
        pattern_results = [
            {
                "image": images[int(idx)].image.url,
                "company_id": images[int(idx)].company_id,
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
        
        # # Clean up temporary file
        # try:
        #     os.remove(fs.path(file_path))
        # except:
        #     pass
        
        return render(request, 'cbir_app/search_results.html', {
            'query_image_url': query_image_url,
            'pattern_results': pattern_results,
            'color_results': color_results,
        })
    
    return render(request, 'cbir_app/search_image.html')

############ API #######################

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

        feature_data = extract_features_color(fs.path(filename))

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
    feature_cache.load()
    token_response = validate_token(request)
    if token_response:
        return token_response

    if 'image' not in request.FILES:
        return Response({"error": "No query image provided."}, status=status.HTTP_400_BAD_REQUEST)

    top_k = int(request.data.get("top_k", 5))
    threshold = float(request.data.get("threshold", 0.0))

    query_image_file = request.FILES['image']
    fs = FileSystemStorage()
    file_path = fs.save(query_image_file.name, query_image_file)
    query_image_url = fs.url(file_path)

    query_features = extract_features_color(fs.path(file_path))
    images = list(Image.objects.all())
    database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

    similarities = find_similar_images_color(query_features, database_features, top_k=top_k)

    pattern_results = [
        {
            "image": images[int(idx)].image.url,
            "company_id": images[int(idx)].company_id,
            "score": similarities["pattern"]["scores"][i]
        }
        for i, idx in enumerate(similarities["pattern"]["indices"])
        if similarities["pattern"]["scores"][i] >= threshold
    ][:top_k]

    color_results = [
        {
            "image": images[int(idx)].image.url,
            "company_id": images[int(idx)].company_id,
            "score": similarities["color"]["scores"][i]
        }
        for i, idx in enumerate(similarities["color"]["indices"])
        if similarities["color"]["scores"][i] >= threshold
    ][:top_k]

    combined_results = combine_pattern_color(similarities, images, top_k=top_k)

    return Response({
        "query_image_url": query_image_url,
        "pattern_results": pattern_results,
        "color_results": color_results,
        "combined_results": combined_results
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

################################ FOR ID #############################################

########### WEB PAGE ##################
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
    feature_cache.load()
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

############ API #######################
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

@csrf_exempt
@api_view(["POST"])
def search_image_id_api(request):
    """
    API to search for similar images based on features.
    Uses in-memory FAISS index and cached features for speed.
    """
    feature_cache.load()
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

########################### UPLOAD BULK IMAGE API ################################
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


#######################   COMBINED RESULRTS   ##########################

@csrf_exempt
def search_image_combined(request):
    feature_cache.load()
    if request.method == "POST":
        import time
        start_time = time.time()

        query_image_file = request.FILES.get('image')
        if not query_image_file:
            return render(request, 'cbir_app/search_image_combined.html', {"error": "No image provided"})

        fs = FileSystemStorage()
        file_path = fs.save(query_image_file.name, query_image_file)
        query_image_url = fs.url(file_path)

        t1 = time.time()
        query_features = extract_features(fs.path(file_path))
        t2 = time.time()
        print(f"[Combined Search] Feature extraction time: {t2 - t1:.3f} seconds")

        images = list(Image.objects.all())
        database_features = [{"pattern": img.pattern_features, "color": img.color_features} for img in images]

        if not database_features:
            return render(request, 'cbir_app/search_image_combined.html', {
                "error": "No images in database.",
                "query_image_url": query_image_url,
                "combined_results": []
            })

        t3 = time.time()
        similarities = find_similar_images(query_features, database_features, top_k=10)
        t4 = time.time()
        print(f"[Combined Search] Similarity search time: {t4 - t3:.3f} seconds")

        # Combine pattern and color scores (average)
        pattern_dict = {int(idx): float(similarities["pattern"]["scores"][i]) for i, idx in enumerate(similarities["pattern"]["indices"])}
        color_dict = {int(idx): float(similarities["color"]["scores"][i]) for i, idx in enumerate(similarities["color"]["indices"])}
        combined = []
        all_indices = set(pattern_dict.keys()) | set(color_dict.keys())
        for idx in all_indices:
            pattern_score = pattern_dict.get(idx, 0)
            color_score = color_dict.get(idx, 0)
            combined_score = (pattern_score + color_score) / 2
            img = images[int(idx)]
            combined.append({
                "image": img.image.url,
                "company_id": img.company_id,
                "combined_score": combined_score
            })
        combined = sorted(combined, key=lambda x: x["combined_score"], reverse=True)[:10]

        total_time = time.time() - start_time
        print(f"[Combined Search] Total API execution time: {total_time:.3f} seconds")

        return render(request, 'cbir_app/search_results_combined.html', {
            "query_image_url": query_image_url,
            "combined_results": combined
        })

    return render(request, 'cbir_app/search_image_combined.html')


@csrf_exempt
@api_view(["POST"])
def search_image_id_api_combined(request):
    """
    API to search for similar images based on pattern, color, and combined similarity.
    Uses in-memory FAISS index and cached features for speed.
    """
    # Feature cache is pre-loaded at startup
    import numpy as np
    import faiss
    import os
    import time
    import datetime

    # Validate token
    start_time = time.time()
    token_response = validate_token(request)
    if token_response:
        return token_response

    if "image" not in request.FILES:
        return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
    
    top_k = int(request.data.get("top_k") or 5)
    p_threshold = float(request.data.get("p_threshold") or 0.0)
    c_threshold = float(request.data.get("c_threshold") or 0.0)
    pattern_threshold = p_threshold / 100
    color_threshold = c_threshold / 100

    company_id = request.data.get("company_id")
    if not company_id:
        return Response({"error": "Missing company_id"}, status=status.HTTP_400_BAD_REQUEST)

    # New: Get which results to return (default to 1)
    return_pattern = int(request.data.get("return_pattern") or 1)
    print("return_pattern", return_pattern)
    return_color = int(request.data.get("return_color") or 1)
    print("return_color", return_color)
    return_combined = int(request.data.get("return_combined") or 1)
    print("return_combined", return_combined)

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
        # Add after line 774 in views.py
        if not feature_cache._loaded:
            print("WARNING: Feature cache not loaded!")
            return Response({"error": "Feature cache not initialized"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                "color_results": [],
                "combined_results": []
            }, status=status.HTTP_200_OK)

        # Similarity search
        t3 = time.time()
        pattern_scores, pattern_indices = pattern_index.search(query_pattern.reshape(1, -1), top_k)
        color_scores, color_indices = color_index.search(query_color.reshape(1, -1), top_k)
        t4 = time.time()
        print(f"FAISS similarity search time: {t4 - t3:.3f} seconds")

        # Format pattern and color results
        def format_results(indices, scores, threshold):
            results = []
            count = 0
            for i, idx in enumerate(indices[0]):
                score = float(scores[0][i])
                if score >= threshold:
                    img = images[int(idx)]
                    results.append({
                        "image_ref_id": getattr(img, "image_ref_id", None),
                        "company_id": img.company_id,
                        "score": score
                    })
                    count += 1
                if count >= top_k:
                    break
            return results

        pattern_results = format_results(pattern_indices, pattern_scores, pattern_threshold)
        color_results = format_results(color_indices, color_scores, color_threshold)

        # Combine pattern and color scores (average)
        pattern_dict = {int(idx): float(pattern_scores[0][i]) for i, idx in enumerate(pattern_indices[0])}
        color_dict = {int(idx): float(color_scores[0][i]) for i, idx in enumerate(color_indices[0])}
        combined = []
        all_indices = set(pattern_dict.keys()) | set(color_dict.keys())
        for idx in all_indices:
            pattern_score = pattern_dict.get(idx, 0)
            color_score = color_dict.get(idx, 0)
            combined_score = (pattern_score + color_score) / 2
            img = images[int(idx)]
            combined.append({
                "image_ref_id": getattr(img, "image_ref_id", None),
                "company_id": img.company_id,
                "combined_score": combined_score
            })
        combined_results = sorted(combined, key=lambda x: x["combined_score"], reverse=True)[:top_k]

        total_time = time.time() - start_time
        print(f"Total API execution time: {total_time:.3f} seconds")

        # Build response based on parameters
        response_data = {
            "message": "Combined search completed.",
            "timestamp": datetime.datetime.now().isoformat(),
        }
        if return_pattern:
            response_data["pattern_results"] = pattern_results
        if return_color:
            response_data["color_results"] = color_results
        if return_combined:
            response_data["combined_results"] = combined_results

        return Response(response_data, status=status.HTTP_200_OK)

    finally:
        os.remove(temp_file_path)

        