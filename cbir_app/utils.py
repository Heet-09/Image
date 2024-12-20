# cbir_app/utils.py
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications import ResNet50
from sklearn.metrics.pairwise import cosine_similarity
import cv2
import numpy as np

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

def find_similar_images(query_features, database_features, top_k=5):
    """
    Finds similar images based on cosine similarity for both pattern and color features.
    Returns indices and similarity scores for each category.
    """
    query_pattern = np.array(query_features["pattern"])
    query_color = np.array(query_features["color"])

    pattern_features = np.array([np.array(f["pattern"]) for f in database_features])
    color_features = np.array([np.array(f["color"]) for f in database_features])

    # Compute cosine similarity
    pattern_similarities = cosine_similarity([query_pattern], pattern_features)[0]
    color_similarities = cosine_similarity([query_color], color_features)[0]

    # Sort and get top_k for each
    pattern_indices = np.argsort(-pattern_similarities)[:top_k]
    color_indices = np.argsort(-color_similarities)[:top_k]

    pattern_scores = pattern_similarities[pattern_indices]
    color_scores = color_similarities[color_indices]

    return {
        "pattern": {"indices": pattern_indices, "scores": pattern_scores},
        "color": {"indices": color_indices, "scores": color_scores},
    }
