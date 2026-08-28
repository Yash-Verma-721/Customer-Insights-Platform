import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from services.vendor_service import update_vendor_profile, add_product, update_product, delete_product

@patch('services.vendor_service.get_connection')
@patch('services.vendor_service.update_vendor_profile_db')
@patch('services.vendor_service.get_vendor_profile')
def test_update_profile(mock_cache, mock_update_db, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    success, msg = update_vendor_profile(1, "Store", "Owner", "123", "GST", "Addr", "City", "State")
    
    assert success is True
    assert "updated successfully" in msg
    mock_conn.commit.assert_called_once()
    mock_cache.clear.assert_called_once()

@patch('services.vendor_service.get_connection')
@patch('services.vendor_service.update_vendor_profile_db')
def test_update_profile_duplicate_name(mock_update_db, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_update_db.side_effect = sqlite3.IntegrityError("Duplicate")
    
    success, msg = update_vendor_profile(1, "Store", "Owner", "123", "GST", "Addr", "City", "State")
    
    assert success is False
    assert "already be taken" in msg
    mock_conn.rollback.assert_called_once()

@patch('services.vendor_service.get_connection')
@patch('services.vendor_service.get_vendor_id_by_user_id')
@patch('services.vendor_service.insert_product')
@patch('services.vendor_service.get_active_marketplace_products')
def test_add_product(mock_cache, mock_insert, mock_get_vendor, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_get_vendor.return_value = 100 # Vendor ID
    
    success, msg = add_product(1, "Prod A", "Cat", 10.0, "Desc", "Active")
    
    assert success is True
    assert "successfully" in msg
    mock_insert.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_cache.clear.assert_called_once()

@patch('services.vendor_service.get_connection')
@patch('services.vendor_service.get_vendor_id_by_user_id')
def test_add_product_invalid_ownership(mock_get_vendor, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_get_vendor.return_value = None # Not a vendor
    
    success, msg = add_product(1, "Prod A", "Cat", 10.0, "Desc", "Active")
    
    assert success is False
    assert "not found" in msg
    mock_conn.commit.assert_not_called()
