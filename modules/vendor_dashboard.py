import streamlit as st
import pandas as pd
import plotly.express as px
from services.order_service import fetch_vendor_order_items
from database.vendor_repository import get_vendor_profile
from database.database import get_vendor_products, get_connection
from database.settlement_repository import get_vendor_settlements
from database.inventory_repository import get_vendor_inventory
from utils.ui_helpers import render_header

def _calculate_kpis(df_orders, df_products, df_settlements, df_inventory):
    kpis = {
        "Total Products": len(df_products),
        "Active Products": len(df_products[df_products['status'] == 'Active']) if not df_products.empty else 0,
        "Products Sold": df_orders['quantity'].sum() if not df_orders.empty else 0,
        "Total Orders": df_orders['order_code'].nunique() if not df_orders.empty else 0,
        "Gross Revenue": df_settlements['gross_amount'].sum() if not df_settlements.empty else 0,
        "Net Revenue": df_settlements['net_amount'].sum() if not df_settlements.empty else 0,
        "Low Stock Products": len(df_inventory[df_inventory['current_stock'] < df_inventory['reorder_level']]) if not df_inventory.empty else 0,
    }
    
    inv_value = 0
    if not df_inventory.empty and not df_products.empty:
        # Merge to get price
        inv_merged = df_inventory.merge(df_products, left_on='product_id', right_on='id', suffixes=('', '_p'))
        if 'price' in inv_merged.columns and 'current_stock' in inv_merged.columns:
            inv_value = (inv_merged['price'] * inv_merged['current_stock']).sum()
    kpis["Inventory Value"] = inv_value
    
    return kpis

def _render_store_overview(kpis):
    st.markdown("### 🏪 Store Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", f"{kpis['Total Orders']:,}")
    col2.metric("Products Sold", f"{kpis['Products Sold']:,}")
    col3.metric("Gross Revenue", f"${kpis['Gross Revenue']:,.2f}")
    col4.metric("Net Revenue", f"${kpis['Net Revenue']:,.2f}")
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total Products", f"{kpis['Total Products']:,}")
    col6.metric("Active Products", f"{kpis['Active Products']:,}")
    col7.metric("Current Inventory Value", f"${kpis['Inventory Value']:,.2f}")
    col8.metric("Low Stock Products", f"{kpis['Low Stock Products']:,}")
    
    st.divider()

def _render_sales_performance(df_orders):
    st.markdown("### 📈 Sales Performance")
    if df_orders.empty:
        st.info("No sales data available to display performance.")
        st.divider()
        return
        
    df_orders['order_date'] = pd.to_datetime(df_orders['order_date'], errors='coerce')
    daily_sales = df_orders.groupby(df_orders['order_date'].dt.date)['quantity'].sum().reset_index()
    daily_revenue = df_orders.groupby(df_orders['order_date'].dt.date)['total_amount'].sum().reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        if not daily_sales.empty:
            fig1 = px.line(daily_sales, x='order_date', y='quantity', title="Daily Sales Trend (Units Sold)", markers=True, color_discrete_sequence=['#3b82f6'])
            st.plotly_chart(fig1, use_container_width=True)
    with col2:
        if not daily_revenue.empty:
            fig2 = px.bar(daily_revenue, x='order_date', y='total_amount', title="Daily Revenue Trend ($)", color_discrete_sequence=['#10b981'])
            st.plotly_chart(fig2, use_container_width=True)
            
    st.divider()

def _render_inventory_health(df_inventory, df_products):
    st.markdown("### 📦 Inventory Health")
    if df_inventory.empty or df_products.empty:
        st.info("No inventory data available.")
        st.divider()
        return
        
    # Vendor specific inventory
    inv_df = df_inventory.merge(df_products, left_on='product_id', right_on='id', suffixes=('', '_p'))
    inv_df['Value'] = inv_df['current_stock'] * inv_df['price']
    inv_df['Status'] = inv_df.apply(lambda x: 'Out of Stock' if x['current_stock'] == 0 else ('Low Stock' if x['current_stock'] < x['reorder_level'] else 'Healthy'), axis=1)
    
    col1, col2 = st.columns(2)
    with col1:
        status_counts = inv_df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig1 = px.pie(status_counts, values='Count', names='Status', title="Current Stock Distribution", hole=0.4, color='Status', color_discrete_map={'Out of Stock': '#ef4444', 'Low Stock': '#f59e0b', 'Healthy': '#10b981'})
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        cat_inv = inv_df.groupby('category')['current_stock'].sum().reset_index()
        fig2 = px.bar(cat_inv, x='category', y='current_stock', title="Category-wise Inventory (Units)", color_discrete_sequence=['#6366f1'])
        st.plotly_chart(fig2, use_container_width=True)
        
    st.divider()

def _render_revenue_analysis(df_settlements):
    st.markdown("### 💰 Revenue Analysis")
    if df_settlements.empty:
        st.info("No settlement data available for revenue analysis.")
        st.divider()
        return
        
    df_settlements['created_at'] = pd.to_datetime(df_settlements['created_at'])
    df_settlements['Month'] = df_settlements['created_at'].dt.to_period('M').astype(str)
    
    monthly_rev = df_settlements.groupby('Month')[['gross_amount', 'net_amount']].sum().reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.line(monthly_rev, x='Month', y=['gross_amount', 'net_amount'], title="Monthly Revenue Trend ($)", markers=True)
        fig1.update_layout(yaxis_title="Amount ($)", legend_title="Metric")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        prod_rev = df_settlements.groupby('product_name')['gross_amount'].sum().reset_index().sort_values('gross_amount', ascending=False).head(5)
        fig2 = px.bar(prod_rev, x='gross_amount', y='product_name', orientation='h', title="Top Products by Revenue ($)", color_discrete_sequence=['#8b5cf6'])
        fig2.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)
        
    st.divider()

def _render_settlement_summary(df_settlements):
    st.markdown("### 🏦 Settlement Summary")
    if df_settlements.empty:
        st.info("No settlements found.")
        st.divider()
        return
        
    gross = df_settlements['gross_amount'].sum()
    comm = df_settlements['commission_amount'].sum()
    net = df_settlements['net_amount'].sum()
    pending = df_settlements[df_settlements['settlement_status'] == 'Pending']['net_amount'].sum()
    paid = df_settlements[df_settlements['settlement_status'] == 'Paid']['net_amount'].sum()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Gross Revenue", f"${gross:,.2f}")
    col2.metric("Commission Deducted", f"${comm:,.2f}")
    col3.metric("Net Settlement", f"${net:,.2f}")
    col4.metric("Paid Settlement", f"${paid:,.2f}")
    col5.metric("Pending Settlement", f"${pending:,.2f}")
    
    # Trend
    df_settlements['created_date'] = df_settlements['created_at'].dt.date
    daily_set = df_settlements.groupby(['created_date', 'settlement_status'])['net_amount'].sum().reset_index()
    fig = px.bar(daily_set, x='created_date', y='net_amount', color='settlement_status', title="Settlement Trend", color_discrete_map={'Paid': '#10b981', 'Pending': '#f59e0b'})
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()

def _render_best_products(df_orders):
    st.markdown("### 🏆 Best Products")
    if df_orders.empty:
        st.info("No orders found to determine best products.")
        st.divider()
        return
        
    prod_sales = df_orders.groupby('product_name').agg({'quantity': 'sum', 'total_amount': 'sum'}).reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        top_qty = prod_sales.sort_values('quantity', ascending=False).head(5)
        st.markdown("**Top Selling Products (By Volume)**")
        st.dataframe(top_qty[['product_name', 'quantity']], use_container_width=True, hide_index=True)
        
    with col2:
        top_rev = prod_sales.sort_values('total_amount', ascending=False).head(5)
        st.markdown("**Highest Revenue Products (By $)**")
        st.dataframe(top_rev[['product_name', 'total_amount']], use_container_width=True, hide_index=True)
        
    st.divider()

def _render_quick_reports():
    st.markdown("### 📑 Quick Reports")
    st.markdown("Download your vendor-specific operational reports.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.button("📄 Sales Report (PDF)", use_container_width=True)
    with col2:
        st.button("📊 Revenue Report (Excel)", use_container_width=True)
    with col3:
        st.button("📦 Inventory Report (CSV)", use_container_width=True)
    with col4:
        st.button("📈 Product Performance (Excel)", use_container_width=True)

def show_vendor_dashboard():
    render_header("Vendor Command Center", "Overview of your business performance on the Customer Insights Platform.", "Dashboard")
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User session not found.")
        return
        
    # Load Data
    order_items = fetch_vendor_order_items(user_id)
    df_orders = pd.DataFrame(order_items)
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        vendor_profile = get_vendor_profile(user_id)
        vendor_id = vendor_profile['id'] if vendor_profile else None
        settlements = get_vendor_settlements(cursor, vendor_id) if vendor_id else []
        inventory = get_vendor_inventory(user_id)
        products = get_vendor_products(user_id)
    finally:
        conn.close()
        
    df_settlements = pd.DataFrame(settlements)
    df_inventory = pd.DataFrame(inventory)
    df_products = pd.DataFrame(products)
    
    kpis = _calculate_kpis(df_orders, df_products, df_settlements, df_inventory)
    
    # Render Sections
    _render_store_overview(kpis)
    _render_sales_performance(df_orders)
    _render_inventory_health(df_inventory, df_products)
    _render_revenue_analysis(df_settlements)
    _render_settlement_summary(df_settlements)
    _render_best_products(df_orders)
    _render_quick_reports()
