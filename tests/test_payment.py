import pytest
from unittest.mock import patch, MagicMock
from services.payment_service import process_vendor_payouts

@patch('services.payment_service.get_connection')
@patch('services.payment_service.get_pending_order_items')
@patch('services.payment_service.create_payment')
def test_commission_calculation(mock_create_payment, mock_get_pending, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    # Return mock row: order_id, vendor_id, commission_rate, gross_amount
    mock_get_pending.return_value = [
        (1, 100, 10.0, 500.0)
    ]
    
    success, msg = process_vendor_payouts()
    
    assert success is True
    assert "Processed 1" in msg
    mock_conn.commit.assert_called_once()
    
    # Assert math: gross=500.0, comm=50.0, net=450.0
    mock_create_payment.assert_called_with(mock_conn.cursor(), 1, 100, 500.0, 50.0, 450.0)

@patch('services.payment_service.get_connection')
@patch('services.payment_service.get_pending_order_items')
def test_duplicate_payment_prevention(mock_get_pending, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    # Empty return simulates that the LEFT JOIN filtered out already-paid items
    mock_get_pending.return_value = []
    
    success, msg = process_vendor_payouts()
    
    assert success is True
    assert "Processed 0" in msg
