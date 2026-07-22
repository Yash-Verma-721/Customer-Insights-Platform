import streamlit as st
from database.database import get_active_marketplace_products

def init_cart():
    if "cart" not in st.session_state:
        st.session_state.cart = {}

def show_marketplace():
    init_cart()
    
    st.markdown("<h2 style='text-align: center; color: #3b82f6;'>Marketplace Catalog</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Browse our products</p>", unsafe_allow_html=True)
    
    col_back, col_space, col_cart = st.columns([1, 4, 1])
    with col_back:
        if st.button("← Back to Home", type="secondary"):
            st.session_state.page = "home"
            st.rerun()
            
    with col_cart:
        total_items = sum(item['qty'] for item in st.session_state.cart.values())
        cart_btn = st.button(f"🛒 Cart ({total_items})", type="primary")
        if cart_btn:
            st.session_state.view_cart = not st.session_state.get("view_cart", False)
            st.rerun()
            
    st.markdown("---")
    
    if st.session_state.get("view_cart", False):
        show_cart()
        return
    
    # Load Products
    products = get_active_marketplace_products()
    
    if not products:
        st.info("No products available at the moment. Please check back later.")
        return
        
    # Sidebar Filters
    with st.sidebar:
        st.markdown("### Filters")
        search_term = st.text_input("Search by Name")
        
        categories = sorted(list(set(p['category'] for p in products if p['category'])))
        selected_category = st.selectbox("Filter by Category", ["All"] + categories)
        
    # Apply Filters
    filtered_products = products
    if search_term:
        filtered_products = [p for p in filtered_products if search_term.lower() in p['product_name'].lower()]
    
    if selected_category != "All":
        filtered_products = [p for p in filtered_products if p['category'] == selected_category]
        
    if not filtered_products:
        st.warning("No products match your search criteria.")
        return
        
    # Display Grid
    cols_per_row = 3
    for i in range(0, len(filtered_products), cols_per_row):
        row_products = filtered_products[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        
        for idx, product in enumerate(row_products):
            with cols[idx]:
                st.markdown(f"""
                <div style='border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 20px; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                    <h4 style='color: #0f172a; margin-top: 0;'>{product['product_name']}</h4>
                    <span style='background: #e2e8f0; color: #475569; padding: 2px 6px; border-radius: 4px; font-size: 11px;'>{product['category'] or 'General'}</span>
                    <h3 style='color: #3b82f6; margin: 10px 0;'>${float(product['price']):.2f}</h3>
                    <p style='color: #64748b; font-size: 14px; height: 40px; overflow: hidden;'>{product['description'] or 'No description available.'}</p>
                    <p style='color: #10b981; font-size: 12px; font-weight: bold;'>In Stock: {product['current_stock']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Add to Cart", key=f"add_{product['id']}", use_container_width=True):
                    pid = str(product['id'])
                    if pid in st.session_state.cart:
                        if st.session_state.cart[pid]['qty'] < product['current_stock']:
                            st.session_state.cart[pid]['qty'] += 1
                            st.toast(f"Increased {product['product_name']} quantity in cart!")
                        else:
                            st.toast(f"Cannot add more! Stock limit reached.")
                    else:
                        st.session_state.cart[pid] = {
                            "name": product['product_name'],
                            "price": float(product['price']),
                            "qty": 1,
                            "max_qty": product['current_stock']
                        }
                        st.toast(f"Added {product['product_name']} to cart!")
                    st.rerun()

def show_cart():
    st.markdown("### Your Shopping Cart")
    
    if not st.session_state.cart:
        st.info("Your cart is empty.")
        return
        
    grand_total = 0.0
    
    for pid, item in list(st.session_state.cart.items()):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            with col1:
                st.write(f"**{item['name']}**")
            with col2:
                st.write(f"${item['price']:.2f}")
            with col3:
                new_qty = st.number_input("Qty", min_value=1, max_value=item['max_qty'], value=item['qty'], key=f"qty_{pid}")
                if new_qty != item['qty']:
                    st.session_state.cart[pid]['qty'] = new_qty
                    st.rerun()
            with col4:
                item_total = item['qty'] * item['price']
                grand_total += item_total
                st.write(f"**Total: ${item_total:.2f}**")
            with col5:
                if st.button("🗑️", key=f"rem_{pid}"):
                    del st.session_state.cart[pid]
                    st.toast("Item removed from cart.")
                    st.rerun()
            st.markdown("---")
            
    st.markdown(f"### Grand Total: ${grand_total:.2f}")
    
    if st.button("Proceed to Checkout", type="primary"):
        st.session_state.page = "checkout"
        st.rerun()
