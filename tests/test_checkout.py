import pytest
from unittest.mock import patch, MagicMock
from services.checkout_service import process_checkout
from core.exceptions import InventoryError

@patch('services.checkout_service.get_connection')
@patch('services.checkout_service.create_order')
@patch('services.checkout_service.get_inventory_stock')
@patch('services.checkout_service.reduce_inventory_stock')
@patch('services.checkout_service.create_order_item')
@patch('services.checkout_service.get_active_marketplace_products')
def test_successful_checkout(mock_cache, mock_create_item, mock_reduce, mock_get_stock, mock_create_order, mock_get_conn):
    # Setup mocks
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_create_order.return_value = 1
    mock_get_stock.return_value = 10
    
    cart = {
        '1': {'qty': 2, 'price': 100.0, 'name': 'Product A'}
    }
    
    # Execute
    success, result = process_checkout("John Doe", "john@test.com", "123", "US", cart)
    
    # Assert
    assert success is True
    assert result.startswith("ORD-")
    mock_conn.cursor.assert_called()
    mock_cursor.execute.assert_called_with("BEGIN TRANSACTION")
    mock_create_order.assert_called()
    mock_get_stock.assert_called_with(mock_cursor, 1)
    mock_reduce.assert_called_with(mock_cursor, 1, 8)
    mock_create_item.assert_called_with(mock_cursor, 1, 1, 2, 100.0)
    mock_conn.commit.assert_called_once()
    mock_cache.clear.assert_called_once()

@patch('services.checkout_service.get_connection')
def test_empty_cart(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    success, result = process_checkout("John", "john@test.com", "123", "US", {})
    # It shouldn't crash, it should just process an empty cart. Wait, process_checkout doesn't check if cart is empty.
    assert success is True
    assert result.startswith("ORD-")
    mock_conn.commit.assert_called_once()

@patch('services.checkout_service.get_connection')
@patch('services.checkout_service.create_order')
@patch('services.checkout_service.get_inventory_stock')
def test_insufficient_stock(mock_get_stock, mock_create_order, mock_get_conn):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_get_stock.return_value = 1 # Only 1 in stock
    
    cart = {
        '1': {'qty': 5, 'price': 100.0, 'name': 'Product A'} # Wants 5
    }
    
    success, msg = process_checkout("John", "john@test.com", "123", "US", cart)
    
    assert success is False
    assert "no longer available" in msg
    mock_conn.rollback.assert_called_once()

@patch('services.checkout_service.get_connection')
@patch('services.checkout_service.create_order')
@patch('services.checkout_service.get_inventory_stock')
def test_rollback_on_failure(mock_get_stock, mock_create_order, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    # Force generic exception
    mock_create_order.side_effect = Exception("DB Failed")
    
    cart = {
        '1': {'qty': 1, 'price': 10.0, 'name': 'Product A'}
    }
    
    success, msg = process_checkout("John", "john@test.com", "123", "US", cart)
    
    assert success is False
    assert "unexpected error" in msg
    mock_conn.rollback.assert_called_once()
