from database.connection import get_connection
from database.vendor_repository import get_vendor_profile, update_vendor_profile_db, get_vendor_id_by_user_id, get_all_vendors_admin, update_vendor_status_db
from database.product_repository import insert_product, update_product_db, delete_product_db, get_active_marketplace_products, get_product_image_db, update_product_image_db
from config.uploads import UploadConfig
from core.logger import get_logger
import os
import uuid
from PIL import Image
from datetime import datetime

logger = get_logger(__name__)

def update_vendor_profile(user_id, vendor_name, owner_name, phone_number, gst_number, address, city, state):
    """Update vendor profile details for a specific user ID."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        update_vendor_profile_db(cursor, user_id, vendor_name, owner_name, phone_number, gst_number, address, city, state)
        conn.commit()
        get_vendor_profile.clear()
        logger.info(f"Vendor profile updated for user_id {user_id}")
        return True, "Profile updated successfully."
    except sqlite3.IntegrityError:
        conn.rollback()
        logger.warning(f"Business Name collision for user_id {user_id}")
        return False, "Business Name may already be taken."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update vendor profile: {str(e)}", exc_info=True)
        return False, "An unexpected error occurred while updating your profile."
    finally:
        conn.close()

def log_vendor_status_change(vendor_id, admin_id, old_status, new_status, reason):
    """Placeholder for future audit logging of vendor status changes."""
    logger.info(f"AUDIT LOG: Vendor {vendor_id} changed from {old_status} to {new_status} by Admin {admin_id}. Reason: {reason}")

def dispatch_vendor_event(vendor_id, event_type, details):
    """
    Generic placeholder for future Email, SMS, Push, WhatsApp, and Marketplace notification integrations.
    """
    logger.info(f"VENDOR EVENT NOTIFICATION: Type={event_type}, Vendor={vendor_id}, Details={details}")

def process_vendor_approval(admin_id, vendor_id, action, reason=None):
    """Process a vendor status transition via state machine validation."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch current status
        cursor.execute("SELECT vendor_status FROM vendors WHERE id = ?", (vendor_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Vendor not found."
            
        current_status = row[0]
        
        # State Machine Validation
        new_status = None
        if action == "Approve":
            if current_status not in ["Pending", "Suspended"]:
                return False, f"Cannot approve vendor from {current_status} state."
            new_status = "Approved"
        elif action == "Reject":
            if current_status != "Pending":
                return False, f"Cannot reject vendor from {current_status} state."
            if not reason:
                return False, "Rejection reason is required."
            new_status = "Rejected"
        elif action == "Suspend":
            if current_status != "Approved":
                return False, f"Cannot suspend vendor from {current_status} state."
            if not reason:
                return False, "Suspension reason is required."
            new_status = "Suspended"
        else:
            return False, "Invalid action."
            
        approved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == "Approved" else None
        
        update_vendor_status_db(cursor, vendor_id, new_status, admin_id, reason, approved_at)
        conn.commit()
        
        log_vendor_status_change(vendor_id, admin_id, current_status, new_status, reason)
        dispatch_vendor_event(vendor_id, "STATUS_CHANGE", {"old": current_status, "new": new_status, "reason": reason})
        
        return True, f"Vendor successfully {new_status.lower()}."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to process vendor approval for vendor_id {vendor_id}: {str(e)}", exc_info=True)
        return False, "An internal error occurred."
    finally:
        conn.close()

def validate_threshold(threshold_str):
    try:
        threshold = int(threshold_str)
        if threshold < 0 or threshold > 100000:
            return False, 0
        return True, threshold
    except (ValueError, TypeError):
        return False, 0

def get_inventory_status(current_stock, threshold):
    """Determine the inventory status based on stock and threshold."""
    if current_stock <= 0:
        return "OUT_OF_STOCK"
    elif current_stock <= threshold:
        return "LOW_STOCK"
    return "IN_STOCK"

def dispatch_inventory_alert(product_name, current_stock, threshold):
    """
    Placeholder for future notifications (Email, SMS, Push, WhatsApp, Admin UI).
    Currently logs the alert without triggering external systems.
    """
    logger.warning(f"INVENTORY ALERT: {product_name} is Low/Out of Stock (Current: {current_stock}, Threshold: {threshold})")

def add_product(user_id, product_name, category, price, description, status, low_stock_threshold=10):
    """Add a new product for a given vendor (using user_id)."""
    
    valid_threshold, parsed_threshold = validate_threshold(low_stock_threshold)
    if not valid_threshold:
        return False, "Low stock threshold must be an integer between 0 and 100000."
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        vendor_id = get_vendor_id_by_user_id(cursor, user_id)
        if not vendor_id:
            return False, "Vendor profile not found."
            
        insert_product(cursor, vendor_id, product_name, category, price, description, status, parsed_threshold)
        conn.commit()
        get_active_marketplace_products.clear()
        logger.info(f"Product '{product_name}' added for vendor_id {vendor_id}")
        return True, "Product added successfully."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to add product for user_id {user_id}: {str(e)}", exc_info=True)
        return False, "An internal error occurred while adding the product."
    finally:
        conn.close()

def update_product(user_id, product_id, product_name, category, price, description, status, low_stock_threshold=10):
    """Update an existing product, ensuring it belongs to the vendor."""
    
    valid_threshold, parsed_threshold = validate_threshold(low_stock_threshold)
    if not valid_threshold:
        return False, "Low stock threshold must be an integer between 0 and 100000."
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        vendor_id = get_vendor_id_by_user_id(cursor, user_id)
        if not vendor_id:
            return False, "Vendor profile not found."
            
        rowcount = update_product_db(cursor, product_id, vendor_id, product_name, category, price, description, status, parsed_threshold)
        if rowcount == 0:
            conn.rollback()
            return False, "Product not found or access denied."
            
        conn.commit()
        get_active_marketplace_products.clear()
        logger.info(f"Product {product_id} updated for vendor_id {vendor_id}")
        return True, "Product updated successfully."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update product {product_id} for user_id {user_id}: {str(e)}", exc_info=True)
        return False, "An internal error occurred while updating the product."
    finally:
        conn.close()

def delete_product(user_id, product_id):
    """Delete a product, ensuring it belongs to the vendor."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        vendor_id = get_vendor_id_by_user_id(cursor, user_id)
        if not vendor_id:
            return False, "Vendor profile not found."
            
        rowcount = delete_product_db(cursor, product_id, vendor_id)
        
        if rowcount == 0:
            conn.rollback()
            return False, "Product not found or access denied."
            
        conn.commit()
        get_active_marketplace_products.clear()
        logger.info(f"Product {product_id} deleted by vendor_id {vendor_id}")
        return True, "Product deleted successfully."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete product {product_id} for user_id {user_id}: {str(e)}", exc_info=True)
        return False, "An internal error occurred while deleting the product."
    finally:
        conn.close()

def update_product_image(user_id, product_id, uploaded_file):
    """Securely replace or upload a new product image."""
    UploadConfig.ensure_directories()
    
    # Validation 1: Size
    if uploaded_file.size > UploadConfig.MAX_FILE_SIZE_BYTES:
        return False, f"File too large. Maximum size is {UploadConfig.MAX_FILE_SIZE_MB}MB."
        
    # Validation 2: MIME Type
    mime_type = uploaded_file.type
    if mime_type not in UploadConfig.ALLOWED_MIMES:
        return False, "Unsupported file format. Please upload JPG, PNG, or WEBP."
        
    # Validation 3: Extension
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in UploadConfig.ALLOWED_EXTENSIONS:
        return False, "Unsupported file extension."
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        vendor_id = get_vendor_id_by_user_id(cursor, user_id)
        if not vendor_id:
            return False, "Vendor profile not found."
            
        old_image_path = get_product_image_db(cursor, product_id, vendor_id)
        
        # Validation 4: Actual Image Content and Optimization
        try:
            img = Image.open(uploaded_file)
            img.verify() # Verify it's an image
            
            # Reset file pointer after verify
            uploaded_file.seek(0)
            img = Image.open(uploaded_file)
            
            # Optimization: Resize maintaining aspect ratio
            img.thumbnail((UploadConfig.MAX_IMAGE_WIDTH, UploadConfig.MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
            
            # Generate safe filename
            safe_filename = f"{uuid.uuid4()}{ext}"
            new_image_path = os.path.join(UploadConfig.UPLOAD_DIR, safe_filename).replace("\\", "/")
            
            # Convert to RGB if saving as JPEG
            if ext in {".jpg", ".jpeg"} and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(new_image_path, quality=UploadConfig.JPEG_QUALITY, optimize=True)
            
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
            
        # Safe Replacement: Update DB
        rowcount = update_product_image_db(cursor, product_id, vendor_id, new_image_path)
        if rowcount == 0:
            if os.path.exists(new_image_path):
                os.remove(new_image_path)
            conn.rollback()
            return False, "Product not found or access denied."
            
        conn.commit()
        get_active_marketplace_products.clear()
        
        # Delete old image ONLY after successful update
        if old_image_path and old_image_path != UploadConfig.PLACEHOLDER_PATH:
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
                
        return True, "Image updated successfully."
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to upload image for product {product_id}: {str(e)}", exc_info=True)
        return False, "An internal error occurred while processing the image."
    finally:
        conn.close()

def remove_product_image(user_id, product_id):
    """Securely remove a product image and update DB to NULL."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        vendor_id = get_vendor_id_by_user_id(cursor, user_id)
        if not vendor_id:
            return False, "Vendor profile not found."
            
        old_image_path = get_product_image_db(cursor, product_id, vendor_id)
        
        rowcount = update_product_image_db(cursor, product_id, vendor_id, None)
        if rowcount == 0:
            conn.rollback()
            return False, "Product not found or access denied."
            
        conn.commit()
        get_active_marketplace_products.clear()
        
        if old_image_path and old_image_path != UploadConfig.PLACEHOLDER_PATH:
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
                
        return True, "Image removed successfully."
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to remove image for product {product_id}: {str(e)}", exc_info=True)
        return False, "An error occurred while removing the image."
    finally:
        conn.close()
