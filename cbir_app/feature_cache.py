import numpy as np
import faiss
from .models import ImageFeature

class FeatureCache:
    def __init__(self):
        self._loaded = False
        self.images = []
        self.pattern_features = None
        self.color_features = None
        self.pattern_index = None
        self.color_index = None

    def load(self):
        if self._loaded:
            return

        all_images = list(ImageFeature.objects.all())
        self.images = all_images
        self.pattern_features = np.array([img.pattern_features for img in all_images], dtype=np.float32)
        self.color_features = np.array([img.color_features for img in all_images], dtype=np.float32)

        if self.pattern_features is None or len(self.pattern_features.shape) < 2:
            raise ValueError(f"pattern_features is not loaded correctly. Shape: {getattr(self.pattern_features, 'shape', None)}")

        if self.pattern_features is not None and self.pattern_features.shape and len(self.pattern_features.shape) > 1:
            self.pattern_index = faiss.IndexFlatIP(self.pattern_features.shape[1])
        else:
            # Handle the error, e.g. log and raise a meaningful exception
            raise ValueError("pattern_features is empty or not loaded correctly")

        faiss.normalize_L2(self.pattern_features)
        self.pattern_index.add(self.pattern_features)

        self.color_index = faiss.IndexFlatIP(self.color_features.shape[1])
        faiss.normalize_L2(self.color_features)
        self.color_index.add(self.color_features)

        self._loaded = True

# Instantiate it without loading immediately
feature_cache = FeatureCache()
