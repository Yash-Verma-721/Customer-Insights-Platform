from database.connection import get_connection
from database.vendor_repository import get_vendor_profile
from database.order_repository import get_vendor_order_items, check_order_item_ownership, update_order_item_status
from services.settlement_service import is_settlement_eligible, generate_settlement_for_item
from core.exceptions import AppError, AuthorizationError
from config.order_status import VendorOrderStatus
from datetime import datetime
import sqlite3

def fetch_vendor_order_items(user_id):
    """Fetch order items specific to the logged-in vendor."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        vendor = get_vendor_profile(user_id)
        if not vendor:
            return []
            
        return get_vendor_order_items(cursor, vendor['id'])
    finally:
        conn.close()

def log_status_change(order_item_id, old_status, new_status, vendor_id, changed_at):
    """
    Placeholder for future audit logging and notifications.
    Currently empty but provides a clean extension point.
    """
    # TODO: Insert into order_item_status_history table
    # TODO: Trigger email/SMS notification to customer if status is Shipped/Delivered
    pass

def is_valid_transition(old_status, new_status):
    """Validate allowed state transitions for order items."""
    if old_status == new_status:
        return False
        
    transitions = {
        VendorOrderStatus.PENDING: [VendorOrderStatus.CONFIRMED, VendorOrderStatus.CANCELLED],
        VendorOrderStatus.CONFIRMED: [VendorOrderStatus.PACKED, VendorOrderStatus.CANCELLED],
        VendorOrderStatus.PACKED: [VendorOrderStatus.SHIPPED, VendorOrderStatus.CANCELLED],
        VendorOrderStatus.SHIPPED: [VendorOrderStatus.DELIVERED, VendorOrderStatus.RETURNED],
        VendorOrderStatus.DELIVERED: [VendorOrderStatus.RETURNED],
        VendorOrderStatus.RETURNED: [VendorOrderStatus.REFUNDED],
        VendorOrderStatus.CANCELLED: [],
        VendorOrderStatus.REFUNDED: []
    }
    
    allowed = transitions.get(old_status, [])
    return new_status in allowed

def change_order_item_status(user_id, order_item_id, old_status, new_status):
    """Update the status of an order item, enforcing ownership and valid transitions."""
    
    if not is_valid_transition(old_status, new_status):
        raise AppError(f"Invalid status transition from {old_status} to {new_status}.")
        
    conn = get_connection()
    try:
        cursor = conn.cursor()
        vendor = get_vendor_profile(user_id)
        if not vendor:
            raise AuthorizationError("Vendor profile not found.")
            
        is_owner = check_order_item_ownership(cursor, order_item_id, vendor['id'])
        if not is_owner:
            raise AuthorizationError("You do not have permission to modify this order item.")
            
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("BEGIN TRANSACTION")
        update_order_item_status(cursor, order_item_id, new_status, updated_at)
        
        log_status_change(order_item_id, old_status, new_status, vendor['id'], updated_at)
        
        conn.commit()
        
        # Trigger Settlement Creation outside the transaction block to avoid nested commit issues,
        # since generate_settlement_for_item manages its own connection/transaction.
        if is_settlement_eligible(new_status):
            generate_settlement_for_item(order_item_id)
            
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
