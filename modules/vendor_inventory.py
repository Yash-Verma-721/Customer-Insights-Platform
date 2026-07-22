import streamlit as st
from database.database import get_vendor_inventory, get_vendor_products, add_inventory, update_inventory

def show_vendor_inventory():
    st.markdown("<h2 style='color: #3b82f6;'>Inventory Management</h2>", unsafe_allow_html=True)
    st.markdown("Track and manage stock levels for your products.")
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User session not found.")
        return

    # Add Inventory Section
    with st.expander("➕ Add Inventory Record"):
        products = get_vendor_products(user_id)
        if not products:
            st.warning("You need to add products before managing inventory.")
        else:
            with st.form("add_inventory_form", clear_on_submit=True):
                product_options = {p['product_name']: p['id'] for p in products}
                selected_product = st.selectbox("Select Product", options=list(product_options.keys()))
                
                col1, col2 = st.columns(2)
                with col1:
                    c_stock = st.number_input("Current Stock", min_value=0, step=1)
                with col2:
                    min_stock = st.number_input("Minimum Stock (Reorder Level)", min_value=0, step=1, value=10)
                
                submit_add = st.form_submit_button("Add Inventory", type="primary")
                if submit_add:
                    product_id = product_options[selected_product]
                    success, msg = add_inventory(user_id, product_id, c_stock, min_stock)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
    st.markdown("---")
    
    # Load Inventory
    inventory = get_vendor_inventory(user_id)
    if not inventory:
        st.info("No inventory records found.")
        return
        
    st.markdown("### Stock Levels")
    
    # Display Inventory and Update logic
    for inv in inventory:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
            col1.write(f"**{inv['product_name']}**")
            col2.write(f"Stock: {inv['current_stock']}")
            col3.write(f"Min: {inv['reorder_level']}")
            col4.write(f"Updated: {inv['updated_at'][:10]}")
            
            with col5:
                update_btn = st.button("Update Stock", key=f"upd_btn_{inv['id']}")
            
            if update_btn:
                st.session_state[f"updating_inv_{inv['id']}"] = True
                st.rerun()
                    
            if st.session_state.get(f"updating_inv_{inv['id']}", False):
                with st.form(f"update_inv_form_{inv['id']}"):
                    st.write(f"Update Stock for {inv['product_name']}")
                    col_u1, col_u2 = st.columns(2)
                    with col_u1:
                        u_stock = st.number_input("Current Stock", min_value=0, step=1, value=int(inv['current_stock']))
                    with col_u2:
                        u_min = st.number_input("Minimum Stock", min_value=0, step=1, value=int(inv['reorder_level']))
                        
                    c_save, c_cancel = st.columns(2)
                    with c_save:
                        save_upd = st.form_submit_button("Save Changes")
                    with c_cancel:
                        cancel_upd = st.form_submit_button("Cancel")
                        
                    if save_upd:
                        success, msg = update_inventory(user_id, inv['id'], u_stock, u_min)
                        if success:
                            st.success("Stock updated successfully.")
                            st.session_state[f"updating_inv_{inv['id']}"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                            
                    if cancel_upd:
                        st.session_state[f"updating_inv_{inv['id']}"] = False
                        st.rerun()
            st.divider()
