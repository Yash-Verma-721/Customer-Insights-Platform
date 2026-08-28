class AppError(Exception):
    """Base application exception."""
    pass

class DatabaseError(AppError):
    pass

class ValidationError(AppError):
    pass

class AuthorizationError(AppError):
    pass

class InventoryError(AppError):
    pass

class PaymentError(AppError):
    pass

class OrderError(AppError):
    pass
