from database.product_repository import get_active_marketplace_products

def fetch_marketplace_catalog():
    """Service function to get marketplace products."""
    return get_active_marketplace_products()
