from database.connection import get_connection
from database.payment_repository import get_pending_order_items, create_payment
from core.logger import get_logger

logger = get_logger(__name__)

def process_vendor_payouts():
    """
    Automatically calculate and generate pending vendor payments for any 
    order items that do not yet have a corresponding payment record.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        pending_payouts = get_pending_order_items(cursor)
        
        for row in pending_payouts:
            order_id = row[0]
            vendor_id = row[1]
            commission_rate = row[2]
            gross_amount = row[3]
            
            comm_amount = gross_amount * (commission_rate / 100.0)
            net_payout = gross_amount - comm_amount
            
            create_payment(cursor, order_id, vendor_id, gross_amount, comm_amount, net_payout)
            
        conn.commit()
        logger.info(f"Processed {len(pending_payouts)} vendor payouts.")
        return True, f"Processed {len(pending_payouts)} vendor payouts."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to process payouts: {str(e)}", exc_info=True)
        return False, "An internal error occurred while processing payouts."
    finally:
        conn.close()
