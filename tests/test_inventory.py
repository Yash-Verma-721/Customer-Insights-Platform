import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from services.inventory_service import add_inventory, update_inventory

@patch('services.inventory_service.get_connection')
@patch('services.inventory_service.check_product_ownership')
@patch('services.inventory_service.insert_inventory')
@patch('services.inventory_service.get_active_marketplace_products')
def test_add_inventory(mock_cache, mock_insert, mock_ownership, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_ownership.return_value = True
    
    success, msg = add_inventory(user_id=1, product_id=10, current_stock=50, reorder_level=10)
    
    assert success is True
    assert "successfully" in msg
    mock_insert.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_cache.clear.assert_called_once()

@patch('services.inventory_service.get_connection')
@patch('services.inventory_service.check_product_ownership')
def test_add_inventory_invalid_ownership(mock_ownership, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_ownership.return_value = False
    
    success, msg = add_inventory(user_id=1, product_id=10, current_stock=50, reorder_level=10)
    
    assert success is False
    assert "access denied" in msg
    mock_conn.commit.assert_not_called()

@patch('services.inventory_service.get_connection')
@patch('services.inventory_service.check_inventory_ownership')
@patch('services.inventory_service.update_inventory_record')
@patch('services.inventory_service.get_active_marketplace_products')
def test_update_inventory(mock_cache, mock_update, mock_ownership, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_ownership.return_value = True
    
    success, msg = update_inventory(user_id=1, inventory_id=5, current_stock=30, reorder_level=5)
    
    assert success is True
    assert "updated" in msg
    mock_update.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_cache.clear.assert_called_once()

# Prevent negative stock is implicitly tested in checkout, but we could add a validation if it existed in inventory_service.
# The current inventory_service doesn't block negative stock explicitly, relying on DB or checkout bounds.
