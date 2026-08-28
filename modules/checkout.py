import streamlit as st
from database.database import process_checkout

def show_checkout():
    st.markdown("<h2 style='text-align: center; color: #3b82f6;'>Checkout</h2>", unsafe_allow_html=True)
    
    if st.button("← Back to Cart", type="secondary"):
        st.session_state.page = "marketplace"
        st.session_state.view_cart = True
        st.rerun()
        
    st.markdown("---")
    
    cart = st.session_state.get("cart", {})
    if not cart:
        st.warning("Your cart is empty. Please add items before checking out.")
        return
        
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Order Summary")
        grand_total = 0.0
        for pid, item in cart.items():
            item_total = item['qty'] * item['price']
            grand_total += item_total
            st.markdown(f"**{item['qty']}x {item['name']}** - ${item_total:.2f}")
            
        st.markdown("---")
        st.markdown(f"#### Grand Total: ${grand_total:.2f}")
        
    with col2:
        st.markdown("### Customer Details")
        with st.form("checkout_form"):
            name = st.text_input("Full Name*")
            email = st.text_input("Email Address*")
            phone = st.text_input("Phone Number*")
            region = st.selectbox("Region*", ["North America", "Europe", "Asia", "South America", "Australia", "Africa"])
            
            submitted = st.form_submit_button("Place Order", type="primary", use_container_width=True)
            
            if submitted:
                if not all([name, email, phone, region]):
                    st.error("Please fill in all required fields.")
                else:
                    success, msg = process_checkout(name, email, phone, region, cart)
                    if success:
                        st.success(f"Order Placed Successfully! Your Order Code is: {msg}")
                        st.session_state.cart = {} # Clear cart
                        st.session_state.order_success = msg
                        st.rerun()
                    else:
                        st.error(f"Failed to place order: {msg}")

    # Display success state after rerun
    if "order_success" in st.session_state:
        st.balloons()
        st.success(f"Thank you for your purchase! Order ID: {st.session_state.order_success}")
        del st.session_state.order_success
