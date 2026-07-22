import os

class UploadConfig:
    # Storage Directory
    UPLOAD_DIR = os.path.join("assets", "product_images")
    
    # Allowed Formats & MIME Types
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
    
    # Validation Limits
    MAX_FILE_SIZE_MB = 5
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Optimization
    MAX_IMAGE_WIDTH = 800
    MAX_IMAGE_HEIGHT = 800
    JPEG_QUALITY = 85
    
    # Fallback
    PLACEHOLDER_PATH = "assets/placeholder_product.png"
    
    @classmethod
    def ensure_directories(cls):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
