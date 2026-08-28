import traceback
from core.logger import get_logger

logger = get_logger(__name__)

def handle_service_error(func):
    """Decorator to catch repository errors, log them, and return a UI-friendly message."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
            return False, "An unexpected error occurred. Please try again later."
    return wrapper
