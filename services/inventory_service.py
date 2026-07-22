from database.connection import get_connection
from database.inventory_repository import check_product_ownership, insert_inventory, check_inventory_ownership, update_inventory_record
from database.product_repository import get_active_marketplace_products
from core.logger import get_logger

logger = get_logger(__name__)

def add_inventory(user_id, product_id, current_stock, reorder_level):
    """Add a new inventory record for a product owned by the vendor."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if not check_product_ownership(cursor, product_id, user_id):
            return False, "Product not found or access denied."
            
        insert_inventory(cursor, product_id, current_stock, reorder_level)
        conn.commit()
        get_active_marketplace_products.clear()
        logger.info(f"Inventory added for product {product_id} by user_id {user_id}")
        return True, "Inventory added successfully."
    except sqlite3.IntegrityError:
        conn.rollback()
        logger.warning(f"Duplicate inventory addition attempted for product {product_id}")
        return False, "Inventory record already exists for this product. Use update instead."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to add inventory: {str(e)}", exc_info=True)
        return False, "An internal error occurred while adding inventory."
    finally:
        conn.close()

def update_inventory(user_id, inventory_id, current_stock, reorder_level):
    """Update an existing inventory record for a product owned by the vendor."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if not check_inventory_ownership(cursor, inventory_id, user_id):
            return False, "Inventory record not found or access denied."
            
        update_inventory_record(cursor, inventory_id, current_stock, reorder_level)
        conn.commit()
        get_active_marketplace_products.clear()
        logger.info(f"Inventory {inventory_id} updated by user_id {user_id}")
        return True, "Inventory updated successfully."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update inventory {inventory_id}: {str(e)}", exc_info=True)
        return False, "An internal error occurred while updating inventory."
    finally:
        conn.close()
