import uuid
from datetime import datetime
from database.order_repository import create_order, create_order_item
from database.inventory_repository import get_inventory_stock, reduce_inventory_stock
from database.product_repository import get_active_marketplace_products
from core.logger import get_logger
from core.exceptions import InventoryError, DatabaseError

logger = get_logger(__name__)

def process_checkout(customer_name, customer_email, customer_phone, region, cart):
    """
    Process an order transaction.
    cart is a dict: {product_id: {'qty': int, 'price': float, 'name': str}}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN TRANSACTION")
        
        total_amount = sum(item['qty'] * item['price'] for item in cart.values())
        order_code = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        order_id = create_order(
            cursor, order_code, customer_name, customer_email, 
            customer_phone, order_date, region, total_amount
        )
        
        for pid_str, item in cart.items():
            pid = int(pid_str)
            qty = int(item['qty'])
            
            current_stock = get_inventory_stock(cursor, pid)
            if current_stock is None:
                raise InventoryError(f"Inventory record missing for product ID: {pid}")
            if current_stock < qty:
                raise InventoryError(f"Insufficient stock for product ID: {pid}. Available: {current_stock}, Requested: {qty}")
                
            new_stock = current_stock - qty
            reduce_inventory_stock(cursor, pid, new_stock)
            
            create_order_item(cursor, order_id, pid, qty, float(item['price']))
            
        conn.commit()
        get_active_marketplace_products.clear()
        logger.info(f"Successfully processed checkout. Order Code: {order_code}")
        return True, order_code
    except InventoryError as e:
        conn.rollback()
        logger.warning(f"Checkout failed due to inventory constraint: {str(e)}")
        return False, "Some items in your cart are no longer available in the requested quantity."
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error during checkout processing: {str(e)}", exc_info=True)
        return False, "An unexpected error occurred during checkout. Please try again."
    finally:
        conn.close()
