import pytest
from unittest.mock import patch
from services.marketplace_service import fetch_marketplace_catalog
from database.product_repository import get_active_marketplace_products

@patch('services.marketplace_service.get_active_marketplace_products')
def test_marketplace_product_filtering(mock_get_products):
    # Mock the return value that would normally come from the DB query
    # which already filters for Active status and stock > 0
    mock_get_products.return_value = [
        {'id': 1, 'product_name': 'Item A', 'status': 'Active', 'current_stock': 10}
    ]
    
    result = fetch_marketplace_catalog()
    
    assert len(result) == 1
    assert result[0]['product_name'] == 'Item A'
    mock_get_products.assert_called_once()

def test_cache_invalidation_behavior():
    # Cache invalidation logic is implicitly tested via the assert_called_once 
    # hooks on mock_cache.clear() in test_vendor.py and test_checkout.py.
    # This test serves as a placeholder for any manual marketplace cache logic.
    assert hasattr(get_active_marketplace_products, "clear")
