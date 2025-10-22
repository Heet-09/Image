# C:\code\Kreon\image\cbir_app\utils.py
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications import ResNet50
from sklearn.metrics.pairwise import cosine_similarity
import cv2
import numpy as np
import faiss
import time


# Load ResNet50 model once at startup
import tensorflow as tf
# Configure TensorFlow for better performance
tf.config.optimizer.set_jit(True)  # Enable XLA compilation
tf.config.threading.set_intra_op_parallelism_threads(0)  # Use all available cores
tf.config.threading.set_inter_op_parallelism_threads(0)

pattern_model = ResNet50(weights="imagenet", include_top=False, pooling="avg")

def extract_features_color(image_path):
    """
    Extracts  improved color features from an image.
    """
    # Load and preprocess the image for pattern features
    img = image.load_img(image_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)

    # Extract pattern features (unchanged - working well)
    pattern_features = pattern_model.predict(img_array).flatten()

    # IMPROVED COLOR FEATURES
    bgr_img = cv2.imread(image_path)
    bgr_img = cv2.resize(bgr_img, (224, 224))

    # 1. LAB color space histogram (better perceptual uniformity)
    lab_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)
    lab_hist = cv2.calcHist([lab_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    lab_features = cv2.normalize(lab_hist, lab_hist).flatten()
    
    # 2. HSV histogram with more bins for better precision
    hsv_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    hsv_hist = cv2.calcHist([hsv_img], [0, 1, 2], None, [12, 8, 8], [0, 180, 0, 256, 0, 256])
    hsv_features = cv2.normalize(hsv_hist, hsv_hist).flatten()
    
    # 3. Dominant colors using K-means
    data = bgr_img.reshape((-1, 3))
    data = np.float32(data)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(data, 6, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Get color percentages
    unique, counts = np.unique(labels, return_counts=True)
    percentages = counts / len(labels)
    
    # Sort by percentage and get dominant colors
    sorted_indices = np.argsort(-percentages)
    dominant_colors = centers[sorted_indices].flatten()
    color_percentages = percentages[sorted_indices]
    
    # 4. Color moments for each channel
    color_moments = []
    for channel in cv2.split(bgr_img.astype(np.float32)):
        mean = np.mean(channel)
        std = np.std(channel)
        skewness = np.mean(((channel - mean) / (std + 1e-7)) ** 3)
        color_moments.extend([mean, std, skewness])
    
    # Combine all color features with weights
    color_features = np.concatenate([
        lab_features * 0.3,      # LAB histogram (30%)
        hsv_features * 0.3,      # HSV histogram (30%) 
        dominant_colors * 0.25,  # Dominant colors (25%)
        color_percentages * 0.1, # Color percentages (10%)
        np.array(color_moments) * 0.05  # Color moments (5%)
    ])

    return {"pattern": pattern_features.tolist(), "color": color_features.tolist()}

# SAFE FUNCTION THAT HANDLES DIMENSION MISMATCHES
def find_similar_images_safe(query_features, database_features, top_k):
    """
    Safe similarity search that handles mixed feature dimensions
    """
    print("In safe similarity search - top_k:", top_k)
    total_start = time.time()

    # Step 1: Prepare features with dimension handling
    t1 = time.time()
    query_pattern = np.array(query_features["pattern"]).astype("float32")
    query_color = np.array(query_features["color"]).astype("float32")

    # Find the maximum dimensions
    all_pattern_dims = [len(query_features["pattern"])] + [len(f["pattern"]) for f in database_features]
    all_color_dims = [len(query_features["color"])] + [len(f["color"]) for f in database_features]
    
    max_pattern_dim = max(all_pattern_dims)
    max_color_dim = max(all_color_dims)
    
    print(f"Pattern dimensions range: {min(all_pattern_dims)} to {max_pattern_dim}")
    print(f"Color dimensions range: {min(all_color_dims)} to {max_color_dim}")

    # Pad query features if needed
    if len(query_pattern) < max_pattern_dim:
        padded_query_pattern = np.zeros(max_pattern_dim, dtype=np.float32)
        padded_query_pattern[:len(query_pattern)] = query_pattern
        query_pattern = padded_query_pattern
    
    if len(query_color) < max_color_dim:
        padded_query_color = np.zeros(max_color_dim, dtype=np.float32)
        padded_query_color[:len(query_color)] = query_color
        query_color = padded_query_color

    # Handle pattern features
    pattern_feature_list = []
    for f in database_features:
        db_pattern = np.array(f["pattern"], dtype=np.float32)
        if len(db_pattern) < max_pattern_dim:
            padded = np.zeros(max_pattern_dim, dtype=np.float32)
            padded[:len(db_pattern)] = db_pattern
            pattern_feature_list.append(padded)
        elif len(db_pattern) > max_pattern_dim:
            pattern_feature_list.append(db_pattern[:max_pattern_dim])
        else:
            pattern_feature_list.append(db_pattern)
    
    pattern_features = np.array(pattern_feature_list, dtype=np.float32)

    # Handle color features  
    color_feature_list = []
    for f in database_features:
        db_color = np.array(f["color"], dtype=np.float32)
        if len(db_color) < max_color_dim:
            padded = np.zeros(max_color_dim, dtype=np.float32)
            padded[:len(db_color)] = db_color
            color_feature_list.append(padded)
        elif len(db_color) > max_color_dim:
            color_feature_list.append(db_color[:max_color_dim])
        else:
            color_feature_list.append(db_color)
    
    color_features = np.array(color_feature_list, dtype=np.float32)
    
    t2 = time.time()
    print(f"Feature preparation time: {t2 - t1:.3f} seconds")
    print(f"Final pattern features shape: {pattern_features.shape}")
    print(f"Final color features shape: {color_features.shape}")

    # Step 2: Pattern similarity with FAISS
    t3 = time.time()
    if pattern_features.shape[1] > 0:
        pattern_index = faiss.IndexFlatIP(pattern_features.shape[1])
        faiss.normalize_L2(pattern_features)
        faiss.normalize_L2(query_pattern.reshape(1, -1))
        pattern_index.add(pattern_features)
        pattern_scores, pattern_indices = pattern_index.search(query_pattern.reshape(1, -1), min(top_k, len(database_features)))
    else:
        pattern_indices = [np.arange(min(top_k, len(database_features)))]
        pattern_scores = [np.ones(min(top_k, len(database_features)))]
    
    t4 = time.time()
    print(f"Pattern FAISS search time: {t4 - t3:.3f} seconds")

    # Step 3: Enhanced Color similarity
    t5 = time.time()
    color_similarities = []
    
    # Normalize query color features
    query_color_norm = query_color / (np.linalg.norm(query_color) + 1e-7)
    
    for db_color in color_features:
        # Normalize database color features
        db_color_norm = db_color / (np.linalg.norm(db_color) + 1e-7)
        
        # Method 1: Cosine similarity
        cosine_sim = np.dot(query_color_norm, db_color_norm)
        
        # Method 2: Chi-square distance (for histogram parts)
        if max_color_dim >= 512:  # We have histogram features
            hist_size = min(512, max_color_dim // 2)  # Use first half as histograms
            query_hist = query_color[:hist_size] + 1e-7
            db_hist = db_color[:hist_size] + 1e-7
            
            chi_square = np.sum(((query_hist - db_hist) ** 2) / (query_hist + db_hist))
            chi_square_sim = 1 / (1 + chi_square)
            
            # Method 3: Intersection similarity
            intersection = np.sum(np.minimum(query_hist, db_hist))
            intersection_sim = intersection / (np.sum(query_hist) + 1e-7)
            
            # Combine all three methods
            combined_sim = (0.4 * cosine_sim + 0.3 * chi_square_sim + 0.3 * intersection_sim)
        else:
            # For smaller feature vectors, use only cosine similarity
            combined_sim = cosine_sim
        
        color_similarities.append(combined_sim)
    
    color_similarities = np.array(color_similarities)
    
    # Get top color matches
    color_indices = np.argsort(-color_similarities)[:min(top_k, len(database_features))]
    color_scores = color_similarities[color_indices]
    
    t6 = time.time()
    print(f"Enhanced color search time: {t6 - t5:.3f} seconds")

    total_end = time.time()
    print(f"Total similarity search time: {total_end - total_start:.3f} seconds")

    return {
        "pattern": {"indices": pattern_indices[0], "scores": pattern_scores[0]},
        "color": {"indices": color_indices, "scores": color_scores},
    }

def extract_features(image_path):
    """
    Extracts pattern  features from an image.
    """
    # Load and preprocess the image for pattern features
    img = image.load_img(image_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)

    # Extract pattern features
    pattern_features = pattern_model.predict(img_array).flatten()

    # Extract color features
    # Load image in BGR format
    bgr_img = cv2.imread(image_path)
    bgr_img = cv2.resize(bgr_img, (224, 224))

    # Convert to HSV color space
    hsv_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    color_features = cv2.calcHist([hsv_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    color_features = cv2.normalize(color_features, color_features).flatten()

    return {"pattern": pattern_features.tolist(), "color": color_features.tolist()}

def find_similar_images(query_features, database_features, top_k):
    print("In find_similar_images - top_k:", top_k)
    total_start = time.time()

    # Step 1: Prepare features
    t1 = time.time()
    query_pattern = np.array(query_features["pattern"]).astype("float32")
    query_color = np.array(query_features["color"]).astype("float32")

    pattern_features = np.array([np.array(f["pattern"]) for f in database_features]).astype("float32")
    color_features = np.array([np.array(f["color"]) for f in database_features]).astype("float32")
    t2 = time.time()
    print(f"Feature preparation time: {t2 - t1:.3f} seconds")

    # Step 2: Pattern similarity with FAISS
    t3 = time.time()
    pattern_index = faiss.IndexFlatIP(pattern_features.shape[1])
    faiss.normalize_L2(pattern_features)
    faiss.normalize_L2(query_pattern.reshape(1, -1))
    pattern_index.add(pattern_features)
    pattern_scores, pattern_indices = pattern_index.search(query_pattern.reshape(1, -1), top_k)
    t4 = time.time()
    print(f"Pattern FAISS search time: {t4 - t3:.3f} seconds")

    # Step 3: Color similarity with FAISS
    t5 = time.time()
    color_index = faiss.IndexFlatIP(color_features.shape[1])
    faiss.normalize_L2(color_features)
    faiss.normalize_L2(query_color.reshape(1, -1))
    color_index.add(color_features)
    color_scores, color_indices = color_index.search(query_color.reshape(1, -1), top_k)
    t6 = time.time()
    print(f"Color FAISS search time: {t6 - t5:.3f} seconds")

    total_end = time.time()
    print(f"Total similarity search time: {total_end - total_start:.3f} seconds")

    return {
        "pattern": {"indices": pattern_indices[0], "scores": pattern_scores[0]},
        "color": {"indices": color_indices[0], "scores": color_scores[0]},
    }

