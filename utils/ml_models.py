import pandas as pd
import numpy as np
import logging
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)

def ml_customer_segmentation(profile_df):
    """
    Performs ML-based customer segmentation using KMeans clustering.
    Automatically selects numeric features, determines optimal K using Silhouette Score,
    and dynamically assigns business-friendly labels based on cluster value.
    
    Args:
        profile_df (pd.DataFrame): Customer profile dataframe (e.g., from build_customer_profile)
        
    Returns:
        tuple: (cluster_df, cluster_summary, metrics, recommendations)
    """
    # 0. Initial Validation
    if profile_df is None or profile_df.empty:
        logger.warning("Profile dataframe is empty or None.")
        return pd.DataFrame(), pd.DataFrame(), {"status": "error", "message": "Empty dataframe"}, []
        
    if len(profile_df) < 2:
        logger.warning("Not enough rows for clustering (minimum 2 required).")
        return profile_df.copy(), pd.DataFrame(), {"status": "error", "message": "Not enough rows"}, []

    # 1. Feature Selection
    numeric_df = profile_df.select_dtypes(include=[np.number])
    ignore_keywords = ['customer', 'segment', 'score', 'rank', 'cluster', 'index', 'order', 'vendor', 'product', 'invoice', 'transaction']
    
    feature_cols = []
    for c in numeric_df.columns:
        c_lower = str(c).lower()
        if c_lower in ['id', 'index']:
            continue
        if any(kw + '_id' in c_lower for kw in ignore_keywords) or c_lower.endswith('id'):
            continue
        if any(kw == c_lower for kw in ignore_keywords):
            continue
        feature_cols.append(c)
    
    if not feature_cols:
        logger.error("No valid numeric features found after filtering.")
        return profile_df.copy(), pd.DataFrame(), {"status": "error", "message": "No numeric features found"}, []
        
    X_raw = profile_df[feature_cols].copy()
    X_raw = X_raw.fillna(X_raw.median(numeric_only=True))
    
    # Check for variance = 0
    if X_raw.var().sum() == 0:
        logger.warning("All numeric features have zero variance (identical values).")
        return profile_df.copy(), pd.DataFrame(), {"status": "error", "message": "Features lack variance"}, []

    # 2. Scaling
    try:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)
    except Exception as e:
        logger.exception("Scaling failed.")
        return profile_df.copy(), pd.DataFrame(), {"status": "error", "message": f"Scaling failed: {str(e)}"}, []
    
    # 3. Determine Optimal K (2 to 8)
    best_k = 2
    best_score = -1.0
    best_model = None
    best_labels = None
    
    max_k = min(8, len(X_raw) - 1)
    if max_k < 2:
        logger.warning("Not enough distinct samples for meaningful clustering after filtering.")
        return profile_df.copy(), pd.DataFrame(), {"status": "error", "message": "Insufficient unique rows for K>1"}, []
        
    try:
        for k in range(2, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            labels = kmeans.fit_predict(X_scaled)
            
            if 1 < len(set(labels)) < len(X_raw):
                score = silhouette_score(X_scaled, labels)
            else:
                score = -1.0
                
            if score > best_score:
                best_score = score
                best_k = k
                best_model = kmeans
                best_labels = labels
    except Exception as e:
        logger.exception("Clustering failed during K search.")
        return profile_df.copy(), pd.DataFrame(), {"status": "error", "message": f"Clustering failed: {str(e)}"}, []

    if best_model is None:
        logger.warning("Clustering failed to find any valid silhouette score, falling back to K=2.")
        try:
            best_k = 2
            best_model = KMeans(n_clusters=best_k, random_state=42, n_init='auto')
            best_labels = best_model.fit_predict(X_scaled)
            best_score = 0.0
        except Exception as e:
            return profile_df.copy(), pd.DataFrame(), {"status": "error", "message": f"Fallback clustering failed: {str(e)}"}, []

    # 4. Rank Clusters and Assign Labels
    cluster_centers = best_model.cluster_centers_
    cluster_scores = []
    
    for i, center in enumerate(cluster_centers):
        score = 0
        for j, col in enumerate(feature_cols):
            val = center[j]
            if 'recency' in str(col).lower():
                score -= val
            else:
                score += val
        cluster_scores.append((i, score))
        
    cluster_scores.sort(key=lambda x: x[1], reverse=True)
    
    if best_k == 2:
        names = ["Premium", "At Risk"]
    elif best_k == 3:
        names = ["Premium", "Regular", "At Risk"]
    elif best_k == 4:
        names = ["Premium", "Loyal", "Occasional", "At Risk"]
    else:
        names = ["Premium", "Loyal", "Regular", "Occasional", "At Risk"]
        
    while len(names) < best_k:
        names.append(f"Tier {len(names)+1} (At Risk)")
        
    rank_to_name = {}
    rank_to_number = {}
    for rank, (cluster_idx, _) in enumerate(cluster_scores):
        rank_to_name[cluster_idx] = names[rank]
        rank_to_number[cluster_idx] = rank + 1
        
    # 5. Assemble Output Data
    cluster_df = profile_df.copy()
    cluster_df['ml_cluster'] = best_labels
    cluster_df['ml_segment'] = cluster_df['ml_cluster'].map(rank_to_name)
    cluster_df['ml_rank'] = cluster_df['ml_cluster'].map(rank_to_number)
    
    total_customers = len(cluster_df)
    
    metrics = {
        "status": "success",
        "optimal_k": best_k,
        "silhouette_score": float(best_score),
        "features_used": feature_cols,
        "cluster_count": best_k,
        "total_customers": total_customers
    }
    
    # Generate Cluster Summary
    cluster_summary = cluster_df.groupby('ml_segment').agg(
        customer_count=('ml_segment', 'count'),
        cluster_rank=('ml_rank', 'first')
    ).reset_index()
    
    cluster_summary['percentage'] = (cluster_summary['customer_count'] / total_customers * 100).round(1)
    
    for feature in ['monetary', 'frequency', 'recency_days']:
        actual_col = next((c for c in feature_cols if feature.split('_')[0] in c.lower()), None)
        if actual_col:
            means = cluster_df.groupby('ml_segment')[actual_col].mean().reset_index()
            means = means.rename(columns={actual_col: f"avg_{feature}"})
            cluster_summary = pd.merge(cluster_summary, means, on='ml_segment', how='left')
    
    cluster_summary = cluster_summary.sort_values('cluster_rank').reset_index(drop=True)
    
    recommendations = _generate_ml_recommendations(cluster_summary)
    
    return cluster_df, cluster_summary, metrics, recommendations

def _generate_ml_recommendations(summary_df):
    """Generate dynamic recommendations based on actual cluster stats."""
    recs = []
    if summary_df.empty:
        return recs
        
    for _, row in summary_df.iterrows():
        segment = row['ml_segment']
        count = row.get('customer_count', 0)
        pct = row.get('percentage', 0)
        
        if segment == 'Premium':
            recs.append(f"Premium ({pct}%): Implement loyalty rewards and upsell premium products to your {count} top customers.")
        elif segment == 'Loyal':
            recs.append(f"Loyal ({pct}%): Cross-sell related items and offer membership upgrades to these {count} engaged customers.")
        elif segment == 'Regular':
            recs.append(f"Regular ({pct}%): Increase engagement through personalized content for this core group of {count} customers.")
        elif segment == 'Occasional':
            recs.append(f"Occasional ({pct}%): Launch targeted promotional campaigns to increase purchase frequency for these {count} buyers.")
        elif 'At Risk' in segment:
            recs.append(f"At Risk ({pct}%): Send aggressive retention offers and win-back campaigns to re-engage these {count} at-risk accounts.")
            
    return recs

def run_ml_segmentation_pipeline(profile_df):
    """
    Safely runs the ML segmentation pipeline using Streamlit caching.
    Stores results in session state.
    """
    import streamlit as st
    
    if profile_df is None or profile_df.empty or len(profile_df) < 2:
        return
        
    try:
        c_df, summ, met, recs = ml_customer_segmentation(profile_df)
        if met.get("status") == "success":
            st.session_state["ml_customer_clusters"] = c_df
            st.session_state["ml_customer_summary"] = summ
            st.session_state["ml_customer_metrics"] = met
            st.session_state["ml_customer_recommendations"] = recs
    except Exception as e:
        logger.exception(f"ML Pipeline execution failed: {e}")

def get_ml_customer_clusters():
    import streamlit as st
    return st.session_state.get("ml_customer_clusters", None)

def get_ml_customer_summary():
    import streamlit as st
    return st.session_state.get("ml_customer_summary", None)

def get_ml_customer_metrics():
    import streamlit as st
    return st.session_state.get("ml_customer_metrics", None)

def get_ml_customer_recommendations():
    import streamlit as st
    return st.session_state.get("ml_customer_recommendations", [])

def ml_sales_forecast(monthly_summary):
    """
    Generate a basic sales forecast for the next period using Linear Regression.
    Args:
        monthly_summary (pd.DataFrame): DataFrame with 'Month' and 'Revenue' columns.
    Returns:
        dict: Forecast metrics including next period predicted revenue, trend, r2 score, and recommendation.
    """
    if monthly_summary is None or monthly_summary.empty or len(monthly_summary) < 3:
        return {"status": "error", "message": "Not enough data for forecasting (minimum 3 periods required)."}
        
    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score
        
        df = monthly_summary.copy()
        df = df.sort_values("Month").reset_index(drop=True)
        
        y = df['Revenue'].values
        X = np.arange(len(y)).reshape(-1, 1)
        
        model = LinearRegression()
        model.fit(X, y)
        
        preds = model.predict(X)
        r2 = r2_score(y, preds)
        
        next_X = np.array([[len(y)]])
        next_pred = max(0, model.predict(next_X)[0])  # Floor at 0
        
        slope = model.coef_[0]
        
        if slope > (0.02 * np.mean(y)):
            trend = "Upward"
            rec = "Sales show a strong upward trend. Ensure inventory levels can support sustained growth."
        elif slope < -(0.02 * np.mean(y)):
            trend = "Downward"
            rec = "Sales are trending downwards. Consider aggressive marketing or discounting to stimulate demand."
        else:
            trend = "Flat"
            rec = "Sales are stabilizing. Focus on customer retention and optimizing profit margins."
            
        confidence = "High" if r2 > 0.7 else "Medium" if r2 > 0.4 else "Low"
            
        return {
            "status": "success",
            "forecast_revenue": float(next_pred),
            "trend": trend,
            "r2_score": float(r2),
            "confidence": confidence,
            "recommendation": rec
        }
    except Exception as e:
        logger.exception(f"Sales forecast failed: {e}")
        return {"status": "error", "message": str(e)}

def generate_marketplace_recommendations(df):
    """
    Generate professional Marketplace Recommendations based on the active dataset.
    Uses actual data for Frequent Bought Together, Cross Sell, Upsell, Trending, Low Stock, and Similar Products.
    Calculates deterministic Recommendation Score based on Sales Weight, Inventory Health, Similarity, and Popularity.
    """
    import pandas as pd
    
    recs = []
    
    if df is None or df.empty:
        return recs
        
    def _find_col(keywords):
        for kw in keywords:
            for col in df.columns:
                if kw.lower() in str(col).lower():
                    return col
        return None
        
    prod_col = _find_col(['product_name', 'item_name', 'product'])
    vendor_col = _find_col(['company', 'vendor', 'supplier', 'seller'])
    cat_col = _find_col(['category', 'department', 'type'])
    price_col = _find_col(['price', 'unit_price', 'cost', 'amount', 'revenue'])
    qty_col = _find_col(['quantity', 'qty'])
    stock_col = _find_col(['stock', 'inventory', 'available'])
    order_col = _find_col(['order_id', 'order', 'invoice', 'transaction'])
    cust_col = _find_col(['customer_id', 'customer', 'buyer', 'client'])
    img_col = _find_col(['product_image', 'image', 'img', 'picture', 'pic'])
    
    if not prod_col:
        return []
        
    agg_dict = {}
    if qty_col: agg_dict[qty_col] = 'sum'
    if price_col: agg_dict[price_col] = 'mean'
    if stock_col: agg_dict[stock_col] = 'max'
    
    group_cols = [prod_col]
    if vendor_col: group_cols.append(vendor_col)
    if cat_col: group_cols.append(cat_col)
    if img_col: group_cols.append(img_col)
    
    if agg_dict:
        try:
            prod_stats = df.groupby(group_cols).agg(agg_dict).reset_index()
        except Exception:
            prod_stats = df[group_cols].drop_duplicates().reset_index()
    else:
        prod_stats = df[group_cols].drop_duplicates().reset_index()

    if qty_col not in prod_stats:
        try:
            counts = df.groupby(group_cols).size().reset_index(name='sales_count')
            prod_stats = pd.merge(prod_stats, counts, on=group_cols, how='left')
            qty_col = 'sales_count'
        except Exception:
            prod_stats['sales_count'] = 1
            qty_col = 'sales_count'
            
    if price_col not in prod_stats:
        prod_stats['temp_price'] = 0.0
        price_col = 'temp_price'
        
    if stock_col not in prod_stats:
        prod_stats['temp_stock'] = 100
        stock_col = 'temp_stock'

    prod_stats = prod_stats.dropna(subset=[prod_col])
    
    max_qty = prod_stats[qty_col].max() if not prod_stats.empty and prod_stats[qty_col].max() > 0 else 1
    max_stock = prod_stats[stock_col].max() if not prod_stats.empty and prod_stats[stock_col].max() > 0 else 1

    added_products = set()

    def add_recommendation(row, r_type, r_reason, business_action, similarity_bonus=0.0):
        p_name = str(row[prod_col])
        if p_name in added_products:
            return
            
        p_vendor = str(row[vendor_col]) if vendor_col else "Marketplace Company"
        p_cat = str(row[cat_col]) if cat_col else "General"
        p_price = float(row[price_col])
        p_qty = int(row[qty_col])
        p_stock = int(row[stock_col])
        p_img = str(row[img_col]) if img_col and img_col in row else None
        
        # Recommendation Score Calculation
        # Weighted score: Sales Weight (40%) + Inventory Health (30%) + Similarity (30%)
        sales_weight = min(1.0, p_qty / max_qty) * 40.0
        
        stock_ratio = p_stock / max_stock
        if 0.1 <= stock_ratio <= 0.8:
            inventory_health = 30.0
        elif stock_ratio > 0.8:
            inventory_health = 15.0
        else:
            inventory_health = 5.0
            
        similarity = similarity_bonus * 30.0
        
        raw_score = sales_weight + inventory_health + similarity
        confidence = min(99.0, max(1.0, round(raw_score, 1)))
        
        popularity = "High" if p_qty >= max_qty * 0.5 else ("Medium" if p_qty >= max_qty * 0.2 else "Low")
        
        recs.append({
            "Product Name": p_name,
            "Vendor": p_vendor,
            "Category": p_cat,
            "Price": p_price,
            "Current Stock": p_stock,
            "Product Image": p_img,
            "Recommendation Type": r_type,
            "Recommendation Reason": r_reason,
            "Business Action": business_action,
            "Confidence Score": f"{confidence}%",
            "Popularity": popularity,
            "Sales Count": p_qty,
            "Factors": {
                "Sales Weight": f"{round(sales_weight, 1)} / 40.0",
                "Inventory Health": f"{round(inventory_health, 1)} / 30.0",
                "Similarity Bonus": f"{round(similarity, 1)} / 30.0"
            }
        })
        added_products.add(p_name)

    # 1. Frequently Bought Together (Order overlap)
    if order_col:
        order_prod = df.dropna(subset=[order_col, prod_col])
        if not order_prod.empty:
            basket = order_prod.groupby(order_col)[prod_col].apply(list)
            pair_counts = {}
            for items in basket:
                unique_items = list(set(items))
                if len(unique_items) > 1:
                    for i in range(len(unique_items)):
                        for j in range(i+1, len(unique_items)):
                            pair = tuple(sorted([unique_items[i], unique_items[j]]))
                            pair_counts[pair] = pair_counts.get(pair, 0) + 1
            if pair_counts:
                top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                for (p1, p2), count in top_pairs:
                    row1 = prod_stats[prod_stats[prod_col] == p1]
                    row2 = prod_stats[prod_stats[prod_col] == p2]
                    if not row1.empty and p1 not in added_products:
                        add_recommendation(row1.iloc[0], "Frequently Bought Together", f"Purchased together in {count} orders with {p2}.", "Bundle with another product", 0.8)
                    if not row2.empty and p2 not in added_products:
                        add_recommendation(row2.iloc[0], "Frequently Bought Together", f"Purchased together in {count} orders with {p1}.", "Bundle with another product", 0.8)

    # 2. Cross Sell Opportunities (Customer overlap)
    if cust_col:
        cust_prod = df.dropna(subset=[cust_col, prod_col])
        if not cust_prod.empty:
            cust_basket = cust_prod.groupby(cust_col)[prod_col].apply(list)
            pair_counts = {}
            for items in cust_basket:
                unique_items = list(set(items))
                if len(unique_items) > 1:
                    for i in range(len(unique_items)):
                        for j in range(i+1, len(unique_items)):
                            pair = tuple(sorted([unique_items[i], unique_items[j]]))
                            pair_counts[pair] = pair_counts.get(pair, 0) + 1
            if pair_counts:
                top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                for (p1, p2), count in top_pairs:
                    row2 = prod_stats[prod_stats[prod_col] == p2]
                    if not row2.empty and p2 not in added_products:
                        add_recommendation(row2.iloc[0], "Cross Sell Opportunities", f"Customers who bought {p1} also bought this product.", "Launch Discount Campaign", 0.7)

    # 3. Trending Products
    trending = prod_stats.sort_values(by=qty_col, ascending=False).head(15)
    for _, row in trending.iterrows():
        if row[prod_col] not in added_products:
            add_recommendation(row, "Trending Products", f"High demand with {int(row[qty_col])} recent sales.", "Monitor Demand", 0.9)

    # 4. Low Stock Alternatives
    if stock_col != 'temp_stock' and cat_col:
        low_stock = prod_stats[prod_stats[stock_col] < 10]
        healthy_stock = prod_stats[prod_stats[stock_col] >= 10]
        
        for _, ls_row in low_stock.iterrows():
            ls_cat = ls_row[cat_col]
            alts = healthy_stock[healthy_stock[cat_col] == ls_cat].sort_values(by=qty_col, ascending=False)
            if not alts.empty:
                alt_row = alts.iloc[0]
                if alt_row[prod_col] not in added_products:
                    add_recommendation(alt_row, "Low Stock Alternatives", f"Healthy inventory alternative to low stock product '{ls_row[prod_col]}'.", "Recommended Replacement", 0.6)

    # 5. Upsell Opportunities
    if price_col != 'temp_price' and cat_col:
        cats = prod_stats[cat_col].unique()
        for c in cats:
            cat_items = prod_stats[prod_stats[cat_col] == c].sort_values(by=price_col, ascending=True)
            if len(cat_items) >= 2:
                upsell_item = cat_items.iloc[-1]
                if upsell_item[prod_col] not in added_products and upsell_item[price_col] > cat_items[price_col].mean():
                    add_recommendation(upsell_item, "Upsell Opportunities", f"Premium option in the {c} category.", "Increase Promotion", 0.8)

    # 6. Similar Products
    if cat_col and vendor_col:
        vendor_cats = prod_stats.groupby([vendor_col, cat_col]).size().reset_index(name='count')
        vendor_cats = vendor_cats[vendor_cats['count'] > 1]
        for _, vc in vendor_cats.head(10).iterrows():
            v = vc[vendor_col]
            c = vc[cat_col]
            sim_items = prod_stats[(prod_stats[vendor_col] == v) & (prod_stats[cat_col] == c)]
            for _, item in sim_items.head(3).iterrows():
                if item[prod_col] not in added_products:
                    add_recommendation(item, "Similar Products", f"Similar to other products from {v} in {c}.", "Compare features", 0.7)

    return sorted(recs, key=lambda x: float(x['Confidence Score'].strip('%')), reverse=True)
