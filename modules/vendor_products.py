import streamlit as st
import pandas as pd
from database.database import get_vendor_products, add_product, update_product, delete_product
from services.vendor_service import update_product_image, remove_product_image, get_inventory_status
from config.uploads import UploadConfig
import os

def show_vendor_products():
    st.markdown("<h2 style='color: #3b82f6;'>Product Management</h2>", unsafe_allow_html=True)
    st.markdown("Manage your inventory, prices, and product details.")
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User session not found.")
        return

    # Add Product Section
    with st.expander("➕ Add New Product"):
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                p_name = st.text_input("Product Name*")
                p_cat = st.text_input("Category")
                p_price = st.number_input("Price*", min_value=0.0, step=0.01)
                p_thresh = st.number_input("Low Stock Threshold", min_value=0, max_value=100000, value=10, step=1)
            with col2:
                p_status = st.selectbox("Status", ["Active", "Inactive"])
                p_desc = st.text_area("Description")
            
            submit_add = st.form_submit_button("Add Product", type="primary")
            if submit_add:
                if not p_name:
                    st.error("Product Name is required.")
                else:
                    success, msg = add_product(user_id, p_name, p_cat, p_price, p_desc, p_status, p_thresh)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
    st.markdown("---")
    
    # Load Products
    products = get_vendor_products(user_id)
    if not products:
        st.info("You haven't added any products yet.")
        return
        
    # Filters & Sorting
    col_filter, col_sort = st.columns(2)
    with col_filter:
        stock_filter = st.selectbox("Filter by Stock Status", ["All", "Normal", "Low Stock", "Out of Stock"])
    with col_sort:
        sort_by = st.selectbox("Sort by", ["Product Name", "Stock Quantity (Low to High)", "Stock Quantity (High to Low)"])
        
    for p in products:
        p['inventory_status'] = get_inventory_status(p['current_stock'], p.get('low_stock_threshold', 10))
        
    if stock_filter == "Low Stock":
        products = [p for p in products if p['inventory_status'] == "LOW_STOCK"]
    elif stock_filter == "Out of Stock":
        products = [p for p in products if p['inventory_status'] == "OUT_OF_STOCK"]
    elif stock_filter == "Normal":
        products = [p for p in products if p['inventory_status'] == "IN_STOCK"]
        
    if sort_by == "Stock Quantity (Low to High)":
        products = sorted(products, key=lambda x: x['current_stock'])
    elif sort_by == "Stock Quantity (High to Low)":
        products = sorted(products, key=lambda x: x['current_stock'], reverse=True)
    else:
        products = sorted(products, key=lambda x: x['product_name'])
        
    st.markdown("### Your Products")
    
    # Display Products and Edit/Delete logic
    for product in products:
        with st.container():
            col_img, col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2, 3])
            
            img_path = product.get('product_image') or UploadConfig.PLACEHOLDER_PATH
            if not os.path.exists(img_path) and img_path != UploadConfig.PLACEHOLDER_PATH:
                img_path = UploadConfig.PLACEHOLDER_PATH
                
            try:
                col_img.image(img_path, use_container_width=True)
            except Exception:
                pass
                
            col1.write(f"**{product['product_name']}**")
            col2.write(f"Cat: {product['category'] or 'N/A'}")
            col3.write(f"${product['price']:.2f}")
            
            # Stock Status Badge
            status_text = product['inventory_status']
            if status_text == "OUT_OF_STOCK":
                col4.error("Out of Stock")
            elif status_text == "LOW_STOCK":
                col4.warning(f"Low Stock ({product['current_stock']})")
            else:
                col4.success(f"In Stock ({product['current_stock']})")
                
            with col5:
                c1, c2 = st.columns(2)
                with c1:
                    edit_btn = st.button("Edit", key=f"edit_btn_{product['id']}")
                with c2:
                    del_btn = st.button("Delete", key=f"del_btn_{product['id']}")
            
            if edit_btn:
                st.session_state[f"editing_{product['id']}"] = True
                st.rerun()
                
            if del_btn:
                success, msg = delete_product(user_id, product['id'])
                if success:
                    st.success("Deleted successfully.")
                    st.rerun()
                else:
                    st.error(msg)
                    
            if st.session_state.get(f"editing_{product['id']}", False):
                with st.form(f"edit_form_{product['id']}"):
                    st.write("Edit Product")
                    e_name = st.text_input("Product Name", value=product['product_name'])
                    e_cat = st.text_input("Category", value=product['category'] or "")
                    e_price = st.number_input("Price", value=float(product['price']), step=0.01)
                    e_thresh = st.number_input("Low Stock Threshold", min_value=0, max_value=100000, value=int(product.get('low_stock_threshold', 10)), step=1)
                    e_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if product['status'] == "Active" else 1)
                    e_desc = st.text_area("Description", value=product['description'] or "")
                    
                    st.markdown("**Product Image**")
                    uploaded_img = st.file_uploader("Replace/Upload Image", type=["jpg", "jpeg", "png", "webp"], key=f"up_{product['id']}")
                    
                    c_save, c_rem, c_cancel = st.columns([2, 2, 2])
                    with c_save:
                        save_edit = st.form_submit_button("Save Changes")
                    with c_rem:
                        if product.get('product_image'):
                            rem_img = st.form_submit_button("Remove Image")
                        else:
                            rem_img = False
                    with c_cancel:
                        cancel_edit = st.form_submit_button("Cancel")
                        
                    if rem_img:
                        r_succ, r_msg = remove_product_image(user_id, product['id'])
                        if r_succ:
                            st.success(r_msg)
                            st.session_state[f"editing_{product['id']}"] = False
                            st.rerun()
                        else:
                            st.error(r_msg)
                            
                    if save_edit:
                        if not e_name:
                            st.error("Product name is required.")
                        else:
                            success, msg = update_product(user_id, product['id'], e_name, e_cat, e_price, e_desc, e_status, e_thresh)
                            if success:
                                if uploaded_img:
                                    img_succ, img_msg = update_product_image(user_id, product['id'], uploaded_img)
                                    if not img_succ:
                                        st.error(img_msg)
                                        st.stop()
                                        
                                st.success("Updated successfully.")
                                st.session_state[f"editing_{product['id']}"] = False
                                st.rerun()
                            else:
                                st.error(msg)
                                
                    if cancel_edit:
                        st.session_state[f"editing_{product['id']}"] = False
                        st.rerun()
            st.divider()
