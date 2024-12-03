# cbir_app/utils.py
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
import numpy as np

# Load ResNet50 model (without the classification head)
model = ResNet50(weights="imagenet", include_top=False, pooling="avg")

def extract_features(image_path):
    """
    Extracts fixed-length features using ResNet50.
    """
    # Load and preprocess the image
    img = image.load_img(image_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    
    # Extract features using ResNet50
    features = model.predict(img_array)
    return features.flatten().tolist()



from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# def find_similar_images(query_features, database_features, top_k=5, queryset=None):
#     """
#     Finds the most similar images based on cosine similarity.
#     The function accepts an optional queryset to fetch the actual objects corresponding to indices.
#     """
#     # Convert features to proper format
#     query_features = np.array(query_features)
#     database_features = np.array([np.array(f) for f in database_features])

#     # Validate dimensions
#     if len(database_features) == 0:
#         raise ValueError("database_features is empty.")
#     if query_features.shape[0] != database_features.shape[1]:
#         raise ValueError("Query features and database features dimensions do not match.")

#     # Compute cosine similarity
#     similarities = cosine_similarity([query_features], database_features)
#     # print("similarities",similarities)
#     sorted_indices = np.argsort(-similarities[0])  # Sort in descending order

#     # If a queryset is provided, return the top_k objects corresponding to the sorted indices
#     if queryset:
#         # Convert queryset to a list to allow indexing
#         queryset_list = list(queryset)
        
#         # Use integer indices to get the corresponding images from the list
#         top_results = [queryset_list[i] for i in sorted_indices[:top_k]]
#         # print("top_results",top_results)
#         return top_results

#     return sorted_indices[:top_k]


# # With printing similar scores
# def find_similar_images(query_features, database_features, top_k=5, queryset=None):
#     """
#     Finds the most similar images based on cosine similarity.
#     Returns top_k indices and their similarity scores.
#     """
#     query_features = np.array(query_features)
#     database_features = np.array([np.array(f) for f in database_features])

#     # Validate dimensions
#     if len(database_features) == 0:
#         raise ValueError("database_features is empty.")
#     if query_features.shape[0] != database_features.shape[1]:
#         raise ValueError("Query features and database features dimensions do not match.")

#     # Compute cosine similarity
#     similarities = cosine_similarity([query_features], database_features)
#     sorted_indices = np.argsort(-similarities[0])  # Sort in descending order
#     sorted_scores = similarities[0][sorted_indices]  # Get corresponding scores

#     if queryset:
#         queryset_list = list(queryset)
#         top_results = [(queryset_list[i], sorted_scores[idx]) for idx, i in enumerate(sorted_indices[:top_k])]
#         return top_results

#     # Return indices and scores
#     return sorted_indices[:top_k], sorted_scores[:top_k]

def find_similar_images(query_features, database_features, top_k=5, queryset=None):
    """
    Finds the most similar images based on cosine similarity.
    Returns top_k indices and their similarity scores.
    """
    query_features = np.array(query_features)
    database_features = np.array([np.array(f) for f in database_features])

    # Validate dimensions
    if len(database_features) == 0:
        raise ValueError("database_features is empty.")
    if query_features.shape[0] != database_features.shape[1]:
        raise ValueError("Query features and database features dimensions do not match.")

    # Compute cosine similarity
    similarities = cosine_similarity([query_features], database_features)
    sorted_indices = np.argsort(-similarities[0])  # Sort in descending order
    sorted_scores = similarities[0][sorted_indices]  # Get corresponding scores

    # Convert indices to Python integers
    sorted_indices = [int(i) for i in sorted_indices]

    if queryset:
        queryset_list = list(queryset)
        top_results = [(queryset_list[i], sorted_scores[idx]) for idx, i in enumerate(sorted_indices[:top_k])]
        return top_results

    # Return indices and scores
    return sorted_indices[:top_k], sorted_scores[:top_k]


