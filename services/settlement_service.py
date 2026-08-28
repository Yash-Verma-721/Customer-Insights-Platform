from database.connection import get_connection
from database.settlement_repository import (
    create_settlement,
    check_settlement_exists,
    get_settlement_source_data,
    update_settlement_status
)
from core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

def is_settlement_eligible(status):
    """Determine if a status transition warrants a settlement."""
    return status == "Delivered"

def dispatch_settlement_event(settlement_id, event_type, details=None):
    """Placeholder hook for future Email/SMS/Payment Gateway integration."""
    logger.info(f"SETTLEMENT EVENT: {event_type} | ID: {settlement_id} | Details: {details}")

def generate_settlement_for_item(order_item_id):
    """Idempotently generate a settlement record for a delivered order item."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Duplicate Protection (Idempotent Check)
        if check_settlement_exists(cursor, order_item_id):
            logger.info(f"Settlement already exists for order_item_id {order_item_id}. Skipping.")
            return True, "Settlement already exists."
            
        # 2. Fetch Source Data
        data = get_settlement_source_data(cursor, order_item_id)
        if not data:
            logger.error(f"Cannot generate settlement for item {order_item_id}: Data not found.")
            return False, "Order item data not found."
            
        vendor_id = data['vendor_id']
        quantity = data['quantity']
        unit_price = data['unit_price']
        commission_rate = data['commission_rate']
        
        # 3. Calculate Earnings
        gross_amount = quantity * unit_price
        commission_amount = gross_amount * (commission_rate / 100.0)
        net_amount = gross_amount - commission_amount
        
        # 4. Save Settlement Snapshot
        create_settlement(
            cursor, 
            vendor_id, 
            order_item_id, 
            gross_amount, 
            commission_rate, 
            commission_amount, 
            net_amount
        )
        conn.commit()
        
        # We can't fetch the exact lastrowid reliably here without modifying create_settlement,
        # but dispatching a general event is sufficient for the hook.
        dispatch_settlement_event("N/A", "SETTLEMENT_CREATED", {"order_item_id": order_item_id})
        
        logger.info(f"Settlement generated for item {order_item_id}. Gross: {gross_amount}, Net: {net_amount}")
        return True, "Settlement generated."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to generate settlement for item {order_item_id}: {str(e)}", exc_info=True)
        return False, "Failed to generate settlement."
    finally:
        conn.close()

def mark_settlement_paid(admin_id, settlement_id):
    """Mark a pending/ready settlement as Paid."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        update_settlement_status(cursor, settlement_id, "Paid", paid_at)
        conn.commit()
        
        dispatch_settlement_event(settlement_id, "SETTLEMENT_PAID")
        logger.info(f"Settlement {settlement_id} marked as Paid by Admin {admin_id}")
        return True, "Settlement marked as Paid."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to mark settlement {settlement_id} as Paid: {str(e)}", exc_info=True)
        return False, "An error occurred updating the settlement."
    finally:
        conn.close()
