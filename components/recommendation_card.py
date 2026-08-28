import streamlit as st
import os

def inject_card_styles():
    """Inject typography styles specifically for the recommendation cards."""
    st.markdown("""
        <style>
        .ai-prod-title {
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 8px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.3;
            min-height: 2.6em; /* Fixed height for consistent layout */
        }
        .ai-prod-meta {
            font-size: 14px;
            color: #a0a0a0;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        /* Custom layout for Price/Stock to ensure no truncation */
        .ai-metric-label {
            font-size: 0.8rem;
            color: #a0a0a0;
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        .ai-metric-value {
            font-size: 1.15rem;
            font-weight: bold;
            color: #ffffff;
            white-space: nowrap;
        }
        .ai-metric-value.stock {
            font-size: 1.05rem;
        }
        /* Confidence Badge */
        .ai-conf-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 16px;
            font-weight: bold;
            font-size: 0.85rem;
            margin-top: 5px;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)


def render_recommendation_card(rec, section):
    """
    Renders a single enterprise-quality recommendation card using native Streamlit.
    """
    with st.container(border=True):
        # Image Assignment
        img_path = rec.get('Product Image')
        if not (img_path and str(img_path) != 'nan' and img_path != '🖼️' and os.path.exists(str(img_path))):
            img_path = "assets/placeholder_product.png"
        
        # Native Streamlit Image (Already normalized to 512x512, white bg)
        st.image(img_path, use_container_width=True)
        
        # Typography: Product Name (Removed semantic tag due to logic unreliability)
        title_html = f'<div class="ai-prod-title">{rec["Product Name"]}</div>'
        st.markdown(title_html, unsafe_allow_html=True)
        
        # Typography: Company and Category
        st.markdown(f'<div class="ai-prod-meta">🏢 {rec["Vendor"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ai-prod-meta" style="margin-bottom: 12px;">🏷 {rec["Category"]}</div>', unsafe_allow_html=True)
        
        # Price and Stock Row (Native Columns, 60/40 ratio)
        p_col, s_col = st.columns([0.6, 0.4])
        
        # Unit Price
        p_col.markdown(f'''
            <div class="ai-metric-label">💰 Unit Price</div>
            <div class="ai-metric-value">${rec['Price']:,.2f}</div>
        ''', unsafe_allow_html=True)
        
        # Available Stock
        s_col.markdown(f'''
            <div class="ai-metric-label">📦 Available Stock</div>
            <div class="ai-metric-value stock">{rec['Current Stock']} Units</div>
        ''', unsafe_allow_html=True)
        
        # Confidence Badge
        conf = float(rec['Confidence Score'].strip('%'))
        if conf >= 80:
            badge_html = f"<div class='ai-conf-badge' style='background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #10b981;'>🟢 High • {conf:.0f}%</div>"
        elif conf >= 60:
            badge_html = f"<div class='ai-conf-badge' style='background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid #f59e0b;'>🟡 Medium • {conf:.0f}%</div>"
        else:
            badge_html = f"<div class='ai-conf-badge' style='background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #ef4444;'>🔴 Low • {conf:.0f}%</div>"
        
        st.markdown(badge_html, unsafe_allow_html=True)
            
        # Recommendation Details Popover (Native Streamlit 1.33+)
        with st.popover("Recommendation Details", use_container_width=True):
            st.markdown(f"**Why Recommended:** {rec['Recommendation Reason']}")
            st.markdown(f"**Business Action:** {rec.get('Business Action', 'Monitor Performance')}")
            st.markdown(f"**Popularity:** {rec['Popularity']} | **Recent Sales:** {rec['Sales Count']:,}")
            
            st.markdown("**Score Breakdown:**")
            for k, v in rec.get("Factors", {}).items():
                st.markdown(f"- **{k}:** {v}")
