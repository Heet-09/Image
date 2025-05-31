# C:\code\Kreon\image\cbir_app\utils.py
# cbir_app/utils.py
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications import ResNet50
from sklearn.metrics.pairwise import cosine_similarity
import cv2
import numpy as np
import faiss
import time


pattern_model = ResNet50(weights="imagenet", include_top=False, pooling="avg")

def extract_features(image_path):
    """
    Extracts both pattern and color features from an image.
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

#def find_similar_images(query_features, database_features, top_k=5):
 #   """
  #  Finds similar images based on cosine similarity for both pattern and color features.
   # Returns indices and similarity scores for each category.
    #"""
    #query_pattern = np.array(query_features["pattern"])
    #query_color = np.array(query_features["color"])

    #pattern_features = np.array([np.array(f["pattern"]) for f in database_features])
    #color_features = np.array([np.array(f["color"]) for f in database_features])

    # Compute cosine similarity
   # pattern_similarities = cosine_similarity([query_pattern], pattern_features)[0]
   # color_similarities = cosine_similarity([query_color], color_features)[0]

    # Sort and get top_k for each
   # pattern_indices = np.argsort(-pattern_similarities)
   # color_indices = np.argsort(-color_similarities)


   # pattern_scores = pattern_similarities[pattern_indices]
   # color_scores = color_similarities[color_indices]

    # print(pattern_scores)

   # return {
    #    "pattern": {"indices": pattern_indices, "scores": pattern_scores},
     #   "color": {"indices": color_indices, "scores": color_scores},
    #}


import time

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

