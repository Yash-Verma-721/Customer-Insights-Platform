import streamlit as st
import pandas as pd
import math
import os
from database.inventory_repository import get_marketplace_inventory_workflow, update_inventory_record, mark_inventory_damaged, get_inventory_logs
from database.product_repository import archive_product_admin, restore_product_admin
from database.connection import get_connection
from utils.ui_helpers import render_header, render_empty_state

# --- Dialogs ---

# --- Dialogs ---

@st.dialog("📦 Receive Stock")
def global_receive_stock_dialog(df):
    inv_options = {}
    for _, r in df.iterrows():
        inv_options[r['inventory_id']] = {
            'display': f"{r['Product']} | {r['SKU']} | Available Stock: {r.get('Available Quantity', 0)}",
            'avail': r.get('Available Quantity', 0)
        }
    
    display_options = [v['display'] for v in inv_options.values()]
    sel_display = st.selectbox("Select Product", display_options)
    
    # Get the corresponding inventory_id
    sel_inv = list(inv_options.keys())[display_options.index(sel_display)]
    avail_stock = inv_options[sel_inv]['avail']
    
    qty = st.number_input("Receive Quantity", step=1, value=10, key="dlg_receive_qty")
    
    c1, c2 = st.columns(2)
    if c1.button("Submit", use_container_width=True):
        if qty <= 0:
            st.error("Receive quantity must be greater than 0.")
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT current_stock FROM inventory WHERE id = ?", (sel_inv,))
            row = cursor.fetchone()
            if not row:
                raise Exception("Inventory record not found.")
            
            db_current_stock = row[0]
            new_db_stock = db_current_stock + qty
            
            cursor.execute("UPDATE inventory SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_db_stock, sel_inv))
            from database.inventory_repository import log_inventory_movement
            log_inventory_movement(cursor, sel_inv, "Receive Stock", qty, "Received via Admin UI")
            conn.commit()
            
            product_name = sel_display.split('|')[0].strip()
            st.session_state.pending_toast = f"✓ Stock updated successfully\n\n{product_name}\n\nAvailable Stock: {avail_stock} ➔ {avail_stock + qty}"
            st.rerun()
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to receive stock: {str(e)}")
        finally:
            conn.close()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()

@st.dialog("📤 Export Data")
def export_dialog(filtered_df):
    st.success("Data export prepared successfully!")
    st.markdown(f"**File:** inventory_export.csv")
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    
    c1, c2 = st.columns(2)
    c1.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name='inventory_export.csv',
        mime='text/csv',
        use_container_width=True
    )
    c1.download_button(
        label="📥 Download Excel",
        data=csv,
        file_name='inventory_export.csv', 
        mime='text/csv',
        use_container_width=True
    )
    if c2.button("Done", use_container_width=True):
        st.rerun()

@st.dialog("🔍 View Details")
def view_details_dialog(product_name, sku, current_stock, inventory_id):
    st.markdown(f"**Product:** {product_name} &nbsp;|&nbsp; **SKU:** {sku} &nbsp;|&nbsp; **Current Stock:** {current_stock}")
    st.divider()
    
    st.write(f"### Inventory History")
    logs = get_inventory_logs(inventory_id)
    if logs:
        log_df = pd.DataFrame(logs)
        st.dataframe(log_df, use_container_width=True)
    else:
        st.info("No history found for this inventory record.")
    
    if st.button("Close", use_container_width=True):
        st.rerun()

@st.dialog("✏️ Edit Inventory & Update Quantity")
def edit_inventory_dialog(product_name, sku, current_stock, reorder_level, inventory_id):
    st.markdown(f"**Product:** {product_name} &nbsp;|&nbsp; **SKU:** {sku} &nbsp;|&nbsp; **Available Stock:** {current_stock}")
    st.divider()
    
    new_qty = st.number_input("New Available Quantity", step=1, value=int(current_stock), key="dlg_edit_qty")
    new_reorder = st.number_input("New Reorder Level", step=1, value=int(reorder_level), key="dlg_edit_reorder")
    
    c1, c2 = st.columns(2)
    if c1.button("Save Changes", use_container_width=True):
        if new_qty < 0:
            st.error("Available Stock cannot be negative.")
            return
        if new_reorder < 0:
            st.error("Reorder Level cannot be negative.")
            return
        if new_qty == int(current_stock) and new_reorder == int(reorder_level):
            st.info("No changes detected.")
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        try:
            qty_diff = new_qty - int(current_stock)
            
            cursor.execute("SELECT current_stock FROM inventory WHERE id = ?", (inventory_id,))
            row = cursor.fetchone()
            if not row:
                raise Exception("Inventory record not found.")
                
            db_current_stock = row[0]
            new_db_current_stock = db_current_stock + qty_diff
            
            update_inventory_record(cursor, inventory_id, new_db_current_stock, new_reorder)
            if qty_diff != 0:
                from database.inventory_repository import log_inventory_movement
                log_inventory_movement(cursor, inventory_id, "Update Quantity", qty_diff, "Manual update via Admin UI")
            conn.commit()
            
            st.session_state.pending_toast = f"✓ Stock updated successfully\n\n{product_name}\n\nAvailable Stock: {current_stock} ➔ {new_qty}"
            st.rerun()
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to update inventory: {str(e)}")
        finally:
            conn.close()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()

@st.dialog("⚠️ Mark Damaged")
def mark_damaged_dialog(product_name, sku, current_stock, inventory_id):
    st.markdown(f"**Product:** {product_name} &nbsp;|&nbsp; **SKU:** {sku} &nbsp;|&nbsp; **Current Stock:** {current_stock}")
    st.divider()
    
    qty = st.number_input("Damaged Quantity", step=1, value=1, key="dlg_damage_qty")
    notes = st.text_input("Notes", value="Damaged in warehouse", key="dlg_damage_notes")
    
    c1, c2 = st.columns(2)
    if c1.button("Submit", use_container_width=True):
        if qty <= 0:
            st.error("Damaged quantity must be greater than 0.")
            return
        if qty > int(current_stock):
            st.error(f"Damaged quantity ({qty}) cannot exceed Available Stock ({current_stock}).")
            return
            
        conn = get_connection()
        cursor = conn.cursor()
        try:
            mark_inventory_damaged(cursor, inventory_id, qty, notes)
            conn.commit()
            
            st.session_state.pending_toast = f"✓ Damaged stock recorded\n\n{product_name}\n\nAvailable Stock: {current_stock} ➔ {int(current_stock) - qty}"
            st.rerun()
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to record damaged stock: {str(e)}")
        finally:
            conn.close()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()

@st.dialog("🗑️ Archive Product")
def archive_product_dialog(product_name, sku, current_stock, product_id, inventory_id):
    st.markdown(f"**Product:** {product_name} &nbsp;|&nbsp; **SKU:** {sku} &nbsp;|&nbsp; **Current Stock:** {current_stock}")
    st.divider()
    
    st.warning(f"Are you sure you want to archive {product_name}? This will hide it from the marketplace but preserve inventory history.")
    
    c1, c2 = st.columns(2)
    if c1.button("Confirm Archive", use_container_width=True):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT status FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            if row and row[0] == 'Archived':
                st.info(f"{product_name} is already archived.")
                return
            
            archive_product_admin(cursor, product_id)
            from database.inventory_repository import log_inventory_movement
            log_inventory_movement(cursor, inventory_id, "Archive Product", 0, "Product archived by Admin")
            conn.commit()
            
            st.session_state.pending_toast = f"✓ Product archived successfully\n\n{product_name}"
            st.rerun()
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to archive product: {str(e)}")
        finally:
            conn.close()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()

@st.dialog("♻️ Restore Product")
def restore_product_dialog(product_name, sku, current_stock, product_id, inventory_id):
    st.markdown(f"**Product:** {product_name} &nbsp;|&nbsp; **SKU:** {sku} &nbsp;|&nbsp; **Current Stock:** {current_stock}")
    st.divider()
    
    st.info(f"Are you sure you want to restore {product_name}? It will become active on the marketplace again.")
    
    c1, c2 = st.columns(2)
    if c1.button("Confirm Restore", use_container_width=True):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT status FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            if row and row[0] == 'Active':
                st.info(f"{product_name} is already active.")
                return
            
            restore_product_admin(cursor, product_id)
            from database.inventory_repository import log_inventory_movement
            log_inventory_movement(cursor, inventory_id, "Restore Product", 0, "Product restored by Admin")
            conn.commit()
            
            st.session_state.pending_toast = f"✓ Product restored successfully\n\n{product_name}"
            st.rerun()
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to restore product: {str(e)}")
        finally:
            conn.close()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()

# --- Main App ---

def _load_inventory_data():
    data = get_marketplace_inventory_workflow()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    
    if not df.empty:
        # 1. Product Image: Actual image if available, else generic placeholder
        if 'Product Image' not in df.columns:
            df['Product Image'] = "🖼️"
            
        # 2. SKU: Derive from Product ID
        if 'product_id' in df.columns:
            df['SKU'] = df['product_id'].apply(lambda x: f"SKU-{str(x).zfill(6)}")
        else:
            df['SKU'] = "N/A"
            
    return df

def on_action_change(inv_id, p_name, p_sku, p_stock, p_reorder, p_id, page):
    key = f"action_{inv_id}_{page}"
    action = st.session_state[key]
    if action != "Select Action":
        if action == "Edit Inventory / Update Quantity":
            st.session_state["dlg_edit_qty"] = int(p_stock)
            st.session_state["dlg_edit_reorder"] = int(p_reorder)
        elif action == "Mark Damaged":
            st.session_state["dlg_damage_qty"] = 1
            st.session_state["dlg_damage_notes"] = "Damaged in warehouse"
        st.session_state.action_to_open = {
            "action": action,
            "inv_id": inv_id,
            "p_name": p_name,
            "p_sku": p_sku,
            "p_stock": p_stock,
            "p_reorder": p_reorder,
            "p_id": p_id
        }
        st.session_state[key] = "Select Action"

def show_marketplace_inventory():
    if "pending_toast" in st.session_state:
        st.toast(st.session_state.pending_toast)
        del st.session_state.pending_toast

    render_header("Inventory Management", "Manage daily operations, stock levels, and procurement.", "Inventory")
    
    df = _load_inventory_data()
    
    # 1. Toolbar
    st.markdown("### Operations Toolbar")
    t1, t2, t3, t4, t5 = st.columns(5)
    
    if t2.button("📦 Receive Stock", use_container_width=True):
        st.session_state["dlg_receive_qty"] = 10
        global_receive_stock_dialog(df)
    
    export_clicked = t3.button("📤 Export", use_container_width=True)
        
    if t4.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    
    st.divider()
    
    if df.empty:
        render_empty_state()
        return

    # 2. Search & Filters
    st.markdown("### Search & Filters")
    f1, f2, f3, f4, f5 = st.columns(5)
    search_query = f1.text_input("Search Products/SKU", key="inv_search")
    
    companies = sorted(df['Company'].dropna().unique().tolist()) if 'Company' in df.columns else []
    company_filter = f2.selectbox("Company", ["All"] + companies)
    
    categories = sorted(df['Category'].dropna().unique().tolist()) if 'Category' in df.columns else []
    category_filter = f3.selectbox("Category", ["All"] + categories)
    
    status_filter = f4.selectbox("Stock Status", ["All", "In Stock", "Low Stock", "Out of Stock", "Archived"])
    
    warehouses = sorted(df['Warehouse'].dropna().unique().tolist()) if 'Warehouse' in df.columns else []
    warehouse_filter = f5.selectbox("Warehouse", ["All"] + warehouses)
    
    # Apply filters
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df['Product'].str.contains(search_query, case=False, na=False) |
            filtered_df['SKU'].str.contains(search_query, case=False, na=False)
        ]
    if company_filter != "All":
        filtered_df = filtered_df[filtered_df['Company'] == company_filter]
    if category_filter != "All":
        filtered_df = filtered_df[filtered_df['Category'] == category_filter]
    if warehouse_filter != "All":
        filtered_df = filtered_df[filtered_df['Warehouse'] == warehouse_filter]
        
    if status_filter != "All":
        if status_filter == "In Stock":
            filtered_df = filtered_df[filtered_df['Available Quantity'] > filtered_df['reorder_level']]
        elif status_filter == "Low Stock":
            filtered_df = filtered_df[(filtered_df['Available Quantity'] <= filtered_df['reorder_level']) & (filtered_df['Available Quantity'] > 0)]
        elif status_filter == "Out of Stock":
            filtered_df = filtered_df[filtered_df['Available Quantity'] <= 0]
        elif status_filter == "Archived":
            filtered_df = filtered_df[filtered_df['Stock Status'] == 'Archived']

    if export_clicked:
        export_dialog(filtered_df)

    st.markdown(f"**{len(filtered_df)} products found**")
    st.divider()
    
    # 3. Inventory Table
    ITEMS_PER_PAGE = 10
    total_pages = math.ceil(len(filtered_df) / ITEMS_PER_PAGE) if len(filtered_df) > 0 else 1
    
    if "inv_page" not in st.session_state:
        st.session_state.inv_page = 1
    if st.session_state.inv_page > total_pages:
        st.session_state.inv_page = max(1, total_pages)
        
    start_idx = (st.session_state.inv_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_df = filtered_df.iloc[start_idx:end_idx]
    
    # Header row
    st.markdown(
        """
        <style>
        .small-font {
            font-size:14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    h_col = st.columns([0.5, 2, 1.5, 1.5, 1.5, 1.5, 1, 1, 1.5, 1.5])
    headers = ["Image", "Product", "SKU", "Company", "Category", "Warehouse", "Available Stock", "Reserved Stock", "Status", "Actions"]
    for col, text in zip(h_col, headers):
        col.markdown(f"**<span class='small-font'>{text}</span>**", unsafe_allow_html=True)
        
    def get_status_badge(qty, reorder, stock_status):
        if stock_status == 'Archived':
            return "🔘 Archived"
        if qty <= 0:
            return "🔴 Out of Stock"
        elif qty <= reorder:
            return "🟡 Low Stock"
        else:
            return "🟢 In Stock"

    for _, row in page_df.iterrows():
        cols = st.columns([0.5, 2, 1.5, 1.5, 1.5, 1.5, 1, 1, 1.5, 1.5])
        
        img_path = row.get('Product Image')
        if img_path and img_path != '🖼️' and os.path.exists(img_path):
            try:
                cols[0].image(img_path, use_container_width=True)
            except:
                cols[0].markdown("<span class='small-font'>🖼️</span>", unsafe_allow_html=True)
        else:
            cols[0].markdown("<span class='small-font'>🖼️</span>", unsafe_allow_html=True)
            
        cols[1].markdown(f"<span class='small-font'>{row.get('Product', 'N/A')}</span>", unsafe_allow_html=True)
        cols[2].markdown(f"<span class='small-font'>{row.get('SKU', 'N/A')}</span>", unsafe_allow_html=True)
        cols[3].markdown(f"<span class='small-font'>{row.get('Company', 'N/A')}</span>", unsafe_allow_html=True)
        cols[4].markdown(f"<span class='small-font'>{row.get('Category', 'N/A')}</span>", unsafe_allow_html=True)
        cols[5].markdown(f"<span class='small-font'>{row.get('Warehouse', 'N/A')}</span>", unsafe_allow_html=True)
        cols[6].markdown(f"<span class='small-font'>{row.get('Available Quantity', 0)}</span>", unsafe_allow_html=True)
        cols[7].markdown(f"<span class='small-font'>{row.get('Reserved Quantity', 0)}</span>", unsafe_allow_html=True)
        
        status_badge = get_status_badge(row.get('Available Quantity', 0), row.get('reorder_level', 0), row.get('Stock Status', ''))
        cols[8].markdown(f"<span class='small-font'>{status_badge}</span>", unsafe_allow_html=True)
        
        with cols[9]:
            inv_id = row.get('inventory_id')
            select_key = f"action_{inv_id}_{st.session_state.inv_page}"
            p_name = row.get('Product')
            p_sku = row.get('SKU')
            p_stock = row.get('Available Quantity', 0)
            p_reorder = row.get('reorder_level', 0)
            p_id = row.get('product_id')
            p_status = row.get('Stock Status')
            
            action_list = ["Select Action", "View Details", "Edit Inventory / Update Quantity", "Mark Damaged"]
            if p_status == 'Archived':
                action_list.append("Restore Product")
            else:
                action_list.append("Archive Product")
            
            st.selectbox(
                "Action",
                action_list,
                key=select_key,
                label_visibility="collapsed",
                on_change=on_action_change,
                kwargs={"inv_id": inv_id, "p_name": p_name, "p_sku": p_sku, "p_stock": p_stock, "p_reorder": p_reorder, "p_id": p_id, "page": st.session_state.inv_page}
            )

    # Pagination controls
    st.markdown("---")
    p1, p2, p3 = st.columns([1, 2, 1])
    if p1.button("Previous", disabled=(st.session_state.inv_page <= 1)):
        st.session_state.inv_page -= 1
        st.rerun()
    p2.markdown(f"<div style='text-align: center'>Page {st.session_state.inv_page} of {total_pages}</div>", unsafe_allow_html=True)
    if p3.button("Next", disabled=(st.session_state.inv_page >= total_pages)):
        st.session_state.inv_page += 1
        st.rerun()
        
    st.divider()

    # Process pending dialogs at the end
    if st.session_state.get('action_to_open'):
        data = st.session_state.action_to_open
        action = data['action']
        if action == "View Details":
            view_details_dialog(data['p_name'], data['p_sku'], data['p_stock'], data['inv_id'])
        elif action == "Edit Inventory / Update Quantity":
            edit_inventory_dialog(data['p_name'], data['p_sku'], data['p_stock'], data['p_reorder'], data['inv_id'])
        elif action == "Mark Damaged":
            mark_damaged_dialog(data['p_name'], data['p_sku'], data['p_stock'], data['inv_id'])
        elif action == "Archive Product":
            archive_product_dialog(data['p_name'], data['p_sku'], data['p_stock'], data['p_id'], data['inv_id'])
        elif action == "Restore Product":
            restore_product_dialog(data['p_name'], data['p_sku'], data['p_stock'], data['p_id'], data['inv_id'])
        
        del st.session_state['action_to_open']

def show_procurement_workflow():
    render_header("Procurement Workflow", "Manage vendor stock procurement and marketplace replenishment.", "Procurement")
    
    df = _load_inventory_data()
    
    if df.empty:
        st.info("No procurement data found.")
        return
        
    st.markdown("### Procurement Status Overview")
    
    pending_reorder = df[df['Procurement Status'] == 'Pending Reorder']
    procured = df[df['Procurement Status'] == 'Procured']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Items Pending Reorder", len(pending_reorder))
    col2.metric("Procured Items", len(procured))
    col3.metric("Total Received Quantity", df['Received Quantity'].sum())
    
    st.markdown("### Active Procurement Queue")
    
    if not pending_reorder.empty:
        st.warning(f"{len(pending_reorder)} products require procurement from vendors.")
        st.dataframe(
            pending_reorder[['Company', 'Product', 'Procurement Status', 'Ordered Quantity', 'Received Quantity', 'Available Quantity', 'Stock Status']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("All products have adequate stock. No pending procurements.")
        
    st.markdown("### Completed Procurements")
    st.dataframe(
        procured[['Company', 'Product', 'Procurement Status', 'Received Quantity', 'Available Quantity', 'Last Procurement Date']],
        use_container_width=True,
        hide_index=True
    )
