import pandas as pd
import re


COLUMN_KEYWORDS = {
    "customer": [
        "customer", "customer_id", "cust", "client", "buyer", "consumer",
        "member", "user_id", "userid", "email", "phone"
    ],
    "order": ["order", "order_id", "invoice", "transaction", "txn", "receipt"],
    "revenue": [
        "revenue", "sales", "amount", "price", "total", "order_value",
        "value", "spend", "net_sales"
    ],
    "date": ["date", "order_date", "purchase_date", "created", "timestamp", "month", "year"],
    "product": ["product", "item", "sku", "goods", "title"],
    "category": ["category", "segment", "type", "class", "brand", "department"],
    "region": ["region", "country", "state", "city", "location", "zone", "territory"],
    "status": ["status", "churn", "cancel", "return", "refund", "active", "inactive"],
}

MARKETPLACE_KEYWORDS = {
    "vendor": ["vendor", "seller", "merchant", "supplier"],
    "product": ["product", "item", "sku", "goods", "title"],
    "category": ["category", "segment", "type", "class", "brand", "department"],
    "order": ["order", "order_id", "invoice", "transaction", "txn", "receipt"],
    "customer": COLUMN_KEYWORDS["customer"],
    "revenue": COLUMN_KEYWORDS["revenue"],
    "date": COLUMN_KEYWORDS["date"],
    "stock": ["stock", "inventory", "available", "on_hand", "quantity"],
    "rating": ["rating", "review", "score", "satisfaction"],
    "delivery": ["delivery", "shipping", "dispatch", "fulfillment"],
    "return": ["return", "refund", "cancel"],
    "region": COLUMN_KEYWORDS["region"],
    "status": COLUMN_KEYWORDS["status"],
}


def detect_customer_columns(df):
    """Return likely customer analytics columns grouped by customer field."""
    detected = {key: [] for key in COLUMN_KEYWORDS}
    normalized_cols = {col: str(col).lower().replace(" ", "_") for col in df.columns}

    for col, lowered in normalized_cols.items():
        for group, keywords in COLUMN_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                detected[group].append(col)

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]) and col not in detected["date"]:
            detected["date"].append(col)

    detected["revenue"] = _numeric_candidates(df, detected["revenue"])
    return detected


def detect_marketplace_columns(df):
    """Return likely operational fields for vendor, product, order, and inventory analytics."""
    detected = {key: [] for key in MARKETPLACE_KEYWORDS}
    normalized_cols = {col: str(col).lower().replace(" ", "_") for col in df.columns}

    for col, lowered in normalized_cols.items():
        for group, keywords in MARKETPLACE_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                detected[group].append(col)

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]) and col not in detected["date"]:
            detected["date"].append(col)

    detected["revenue"] = _numeric_candidates(df, detected["revenue"])
    detected["stock"] = _numeric_candidates(df, detected["stock"])
    detected["rating"] = _numeric_candidates(df, detected["rating"])
    return detected


def first_detected(detected, key):
    values = detected.get(key, [])
    return values[0] if values else None


def _matches_keyword(text, keywords):
    if not text:
        return False
    text_normalized = str(text).lower().replace("_", " ").replace("-", " ")
    for keyword in keywords:
        keyword_normalized = str(keyword).lower().replace("_", " ").replace("-", " ")
        if re.search(r"\b" + re.escape(keyword_normalized) + r"\b", text_normalized):
            return True
    return False


def _numeric_candidates(df, columns, min_valid_ratio=0.6):
    numeric_cols = []
    for col in columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
            continue
        coerced = pd.to_numeric(df[col], errors="coerce")
        valid_ratio = coerced.notna().mean() if len(coerced) else 0
        if valid_ratio >= min_valid_ratio:
            numeric_cols.append(col)
    return numeric_cols


def _numeric_series(df, col):
    if not col:
        return None
    return pd.to_numeric(df[col], errors="coerce")


def _date_series(df, col):
    if not col:
        return None
    return pd.to_datetime(df[col], errors="coerce")


def _score_series(series, ascending=True):
    if series.nunique(dropna=True) <= 1:
        return pd.Series(3, index=series.index)
    ranked = series.rank(method="first", ascending=ascending)
    try:
        return pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        return pd.Series(3, index=series.index)


def _segment_customer(row):
    rfm_score = row.get("rfm_score", 0)
    frequency = row.get("frequency", 0)

    if rfm_score >= 13:
        return "Champions"
    if rfm_score >= 10 and frequency >= 2:
        return "Loyal Customers"
    if rfm_score >= 8:
        return "Potential Loyalists"
    if row.get("recency_score", 3) <= 2 and row.get("monetary_score", 3) >= 4:
        return "At Risk"
    if frequency <= 1:
        return "One-Time Customers"
    return "Needs Attention"


def build_customer_profile(df, detected=None):
    """Build customer-level KPIs and an RFM-like profile from a raw dataset."""
    if detected is None:
        detected = detect_customer_columns(df)

    customer_col = first_detected(detected, "customer")
    detected = dict(detected)
    detected["revenue"] = _numeric_candidates(df, detected.get("revenue", []))

    revenue_col = first_detected(detected, "revenue")
    date_col = first_detected(detected, "date")
    product_col = first_detected(detected, "product")
    category_col = first_detected(detected, "category")
    region_col = first_detected(detected, "region")
    status_col = first_detected(detected, "status")

    working = df.copy()
    if customer_col is None:
        customer_col = "_customer_record_id"
        working[customer_col] = working.index.astype(str)

    revenue = _numeric_series(working, revenue_col)
    if revenue is None:
        revenue_col = "_transaction_value"
        working[revenue_col] = 1
    else:
        working[revenue_col] = revenue.fillna(0)

    dates = _date_series(working, date_col)
    has_dates = dates is not None and dates.notna().any()
    if has_dates:
        working["_customer_event_date"] = dates

    grouped = working.groupby(customer_col, dropna=False)
    is_customer_level = working[customer_col].is_unique if customer_col else False
    
    profile = grouped.agg(
        monetary=(revenue_col, "sum"),
    )
    
    if is_customer_level:
        freq_col = None
        
        for col in working.columns:
            if _matches_keyword(col, ["frequency", "orders", "transactions", "purchases", "count"]):
                # Ensure the matched column is actually numeric (avoids matching string columns like 'Frequency of Purchases' = 'Fortnightly')
                if pd.api.types.is_numeric_dtype(working[col]):
                    freq_col = col
                    break
        if freq_col:
            profile["frequency"] = grouped[freq_col].first()
        else:
            profile["frequency"] = grouped.size()
    else:
        order_col = first_detected(detected, "order")
        if order_col:
            profile["frequency"] = grouped[order_col].nunique()
        else:
            profile["frequency"] = grouped.size()
            
    # Ensure frequency is numeric and > 0 to prevent division errors
    profile["frequency"] = pd.to_numeric(profile["frequency"], errors='coerce').fillna(1)
    profile["frequency"] = profile["frequency"].replace(0, 1)
    
    profile["avg_order_value"] = profile["monetary"] / profile["frequency"]
    profile = profile.reset_index().rename(columns={customer_col: "customer"})

    if has_dates:
        latest_date = working["_customer_event_date"].max()
        last_purchase = grouped["_customer_event_date"].max().reset_index(drop=True)
        profile["last_purchase"] = last_purchase
        profile["recency_days"] = (latest_date - profile["last_purchase"]).dt.days.fillna(0)
    else:
        profile["last_purchase"] = pd.NaT
        profile["recency_days"] = 0

    profile["recency_score"] = _score_series(profile["recency_days"], ascending=False)
    profile["frequency_score"] = _score_series(profile["frequency"], ascending=True)
    profile["monetary_score"] = _score_series(profile["monetary"], ascending=True)
    profile["rfm_score"] = (
        profile["recency_score"] + profile["frequency_score"] + profile["monetary_score"]
    )
    profile["segment"] = profile.apply(_segment_customer, axis=1)

    total_customers = profile["customer"].nunique()
    total_revenue = float(profile["monetary"].sum())
    repeat_customers = int((profile["frequency"] > 1).sum())
    one_time_customers = int((profile["frequency"] == 1).sum())
    high_value_threshold = profile["monetary"].quantile(0.8) if len(profile) else 0
    high_value_customers = int((profile["monetary"] >= high_value_threshold).sum()) if len(profile) else 0

    top_count = max(1, int(round(total_customers * 0.10))) if total_customers else 0
    top_revenue = profile.nlargest(top_count, "monetary")["monetary"].sum() if top_count else 0
    top_10_revenue_share = (top_revenue / total_revenue * 100) if total_revenue else 0

    metrics = {
        "total_records": int(len(df)),
        "total_customers": int(total_customers),
        "total_revenue": total_revenue,
        "avg_order_value": float(working[revenue_col].mean()) if len(working) else 0,
        "purchase_frequency": float(profile["frequency"].mean()) if total_customers else 0,
        "repeat_rate": float(repeat_customers / total_customers * 100) if total_customers else 0,
        "one_time_customers": one_time_customers,
        "high_value_customers": high_value_customers,
        "top_10_revenue_share": float(top_10_revenue_share),
        "segments": profile["segment"].value_counts().to_dict(),
        "has_customer_column": first_detected(detected, "customer") is not None,
        "has_revenue_column": first_detected(detected, "revenue") is not None,
        "has_date_column": has_dates,
    }

    columns = {
        "customer": first_detected(detected, "customer"),
        "revenue": first_detected(detected, "revenue"),
        "date": first_detected(detected, "date"),
        "product": product_col,
        "category": category_col,
        "region": region_col,
        "status": status_col,
    }

    return profile, metrics, columns


def money(value):
    return f"{value:,.2f}"


def percent(value):
    return f"{value:.1f}%"


def customer_recommendations(metrics):
    recommendations = []

    if metrics["repeat_rate"] < 25:
        recommendations.append(
            "Prioritize retention campaigns because repeat purchase rate is low."
        )
    else:
        recommendations.append(
            "Protect loyal customer cohorts with lifecycle offers and service follow-ups."
        )

    if metrics["top_10_revenue_share"] > 50:
        recommendations.append(
            "Reduce concentration risk by growing mid-value customers, not only the top accounts."
        )

    if metrics["one_time_customers"] > metrics["total_customers"] * 0.4:
        recommendations.append(
            "Launch a first-to-second purchase journey for one-time customers."
        )

    if not recommendations:
        recommendations.append(
            "Use segment-level campaigns to improve purchase frequency and average order value."
        )

    return recommendations


def build_vendor_profile(df, detected=None):
    """Build vendor-level KPIs and performance rankings from a raw dataset."""
    if detected is None:
        detected = detect_marketplace_columns(df)

    vendor_col = first_detected(detected, "vendor")
    detected = dict(detected)
    detected["revenue"] = _numeric_candidates(df, detected.get("revenue", []))
    detected["rating"] = _numeric_candidates(df, detected.get("rating", []))

    revenue_col = first_detected(detected, "revenue")
    date_col = first_detected(detected, "date")
    product_col = first_detected(detected, "product")
    category_col = first_detected(detected, "category")
    region_col = first_detected(detected, "region")
    rating_col = first_detected(detected, "rating")
    status_col = first_detected(detected, "status")

    working = df.copy()
    if vendor_col is None:
        vendor_col = "_vendor_record_id"
        working[vendor_col] = "Default Vendor"

    revenue = _numeric_series(working, revenue_col)
    if revenue is None:
        revenue_col = "_transaction_value"
        working[revenue_col] = 1
    else:
        working[revenue_col] = revenue.fillna(0)

    if rating_col:
        rating = _numeric_series(working, rating_col)
        working[rating_col] = rating.fillna(0)

    grouped = working.groupby(vendor_col, dropna=False)
    
    profile = grouped.agg(
        revenue=(revenue_col, "sum"),
    )
    
    order_col = first_detected(detected, "order")
    if order_col:
        profile["orders"] = grouped[order_col].nunique()
    else:
        profile["orders"] = grouped.size()
        
    profile["orders"] = profile["orders"].replace(0, 1)
    profile["avg_order_value"] = profile["revenue"] / profile["orders"]
    
    if rating_col:
        profile["avg_rating"] = grouped[rating_col].mean()
    else:
        profile["avg_rating"] = pd.Series(dtype=float)
        
    # Fulfillment/Refund percentage logic if status exists
    if status_col:
        # Just simple counting for status fields
        def _fulfillment_pct(series):
            total = len(series)
            if total == 0:
                return 0.0
            # Assume successful words vs failure words
            success_mask = series.astype(str).str.lower().str.contains("success|complete|deliver|active|ship", na=False)
            return (success_mask.sum() / total) * 100
        
        profile["fulfillment_pct"] = grouped[status_col].apply(_fulfillment_pct)
    else:
        profile["fulfillment_pct"] = pd.Series(dtype=float)

    profile = profile.reset_index().rename(columns={vendor_col: "vendor"})

    # Vendor Ranking based on Revenue
    profile["revenue_rank"] = profile["revenue"].rank(method="dense", ascending=False)
    profile["order_rank"] = profile["orders"].rank(method="dense", ascending=False)
    
    # Calculate global metrics
    total_vendors = profile["vendor"].nunique()
    total_revenue = float(profile["revenue"].sum())
    total_orders = int(profile["orders"].sum())
    
    top_vendor = profile.loc[profile["revenue_rank"] == 1, "vendor"].iloc[0] if not profile.empty else None

    metrics = {
        "total_records": int(len(df)),
        "total_vendors": int(total_vendors),
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order_value": float(working[revenue_col].mean()) if len(working) else 0,
        "top_vendor_by_revenue": top_vendor,
        "has_vendor_column": first_detected(detected, "vendor") is not None,
        "has_revenue_column": first_detected(detected, "revenue") is not None,
        "has_date_column": first_detected(detected, "date") is not None,
        "has_rating_column": first_detected(detected, "rating") is not None,
    }

    columns = {
        "vendor": first_detected(detected, "vendor"),
        "revenue": first_detected(detected, "revenue"),
        "date": first_detected(detected, "date"),
        "product": product_col,
        "category": category_col,
        "region": region_col,
        "rating": rating_col,
        "status": status_col,
    }

    return profile, metrics, columns


def build_inventory_profile(df, detected=None):
    """Build product-level inventory analytics KPIs from a raw dataset."""
    if detected is None:
        detected = detect_marketplace_columns(df)

    product_col = first_detected(detected, "product")
    detected = dict(detected)
    detected["revenue"] = _numeric_candidates(df, detected.get("revenue", []))
    detected["stock"] = _numeric_candidates(df, detected.get("stock", []))
    detected["rating"] = _numeric_candidates(df, detected.get("rating", []))

    revenue_col = first_detected(detected, "revenue")
    stock_col = first_detected(detected, "stock")
    rating_col = first_detected(detected, "rating")
    category_col = first_detected(detected, "category")
    vendor_col = first_detected(detected, "vendor")

    working = df.copy()
    if product_col is None:
        product_col = "_product_record_id"
        working[product_col] = "Default Product"

    if revenue_col:
        price = _numeric_series(working, revenue_col)
        working[revenue_col] = price.fillna(0)
        
    if stock_col:
        stock = _numeric_series(working, stock_col)
        working[stock_col] = stock.fillna(0)
        
    if rating_col:
        rating = _numeric_series(working, rating_col)
        working[rating_col] = rating.fillna(0)

    grouped = working.groupby(product_col, dropna=False)

    profile = pd.DataFrame(index=grouped.groups.keys())
    
    if category_col:
        profile["category"] = grouped[category_col].first()
    else:
        profile["category"] = "Uncategorized"
        
    if vendor_col:
        profile["vendor"] = grouped[vendor_col].first()

    if stock_col:
        profile["stock"] = grouped[stock_col].sum()
    else:
        profile["stock"] = pd.Series(dtype=float)

    if revenue_col:
        profile["avg_price"] = grouped[revenue_col].mean()
    else:
        profile["avg_price"] = pd.Series(dtype=float)

    if stock_col and revenue_col:
        profile["inventory_value"] = profile["stock"] * profile["avg_price"]
    else:
        profile["inventory_value"] = pd.Series(dtype=float)

    if rating_col:
        profile["avg_rating"] = grouped[rating_col].mean()
    else:
        profile["avg_rating"] = pd.Series(dtype=float)

    order_col = first_detected(detected, "order")
    if order_col:
        profile["orders"] = grouped[order_col].nunique()
    else:
        profile["orders"] = grouped.size()

    profile = profile.reset_index().rename(columns={"index": "product", product_col: "product"})
    
    if "index" in profile.columns and "product" in profile.columns:
        profile = profile.drop(columns=["index"])

    # Extract business-friendly product name for labels if available
    product_cols = detected.get("product", [])
    label_col = None
    if len(product_cols) > 1:
        for col in product_cols:
            if "name" in str(col).lower() or "title" in str(col).lower():
                label_col = col
                break
                
    if label_col and label_col != product_col:
        name_mapping = working.drop_duplicates(subset=[product_col]).set_index(product_col)[label_col]
        # Replace the product ID with the product Name in the profile for UI display
        profile["product"] = profile["product"].map(name_mapping).fillna(profile["product"])

    # Calculate total products based on the unique grouped IDs (row count), not the mapped display labels
    total_products = len(profile)
    total_categories = profile["category"].nunique() if "category" in profile.columns else 0
    
    if stock_col:
        out_of_stock_count = int((profile["stock"] <= 0).sum())
        low_stock_count = int(((profile["stock"] > 0) & (profile["stock"] < 10)).sum())
    else:
        out_of_stock_count = 0
        low_stock_count = 0

    total_inventory_value = float(profile["inventory_value"].sum()) if stock_col and revenue_col else 0
    
    valid_ratings = profile["avg_rating"].dropna()
    avg_catalog_rating = float(valid_ratings.mean()) if len(valid_ratings) > 0 else 0
    
    valid_prices = profile["avg_price"].dropna()
    avg_catalog_price = float(valid_prices.mean()) if len(valid_prices) > 0 else 0

    top_categories = profile["category"].value_counts().head(5).to_dict() if "category" in profile.columns else {}
    top_products = profile.nlargest(5, "orders")[["product", "orders"]].set_index("product")["orders"].to_dict() if not profile.empty else {}

    metrics = {
        "total_products": int(total_products),
        "total_categories": int(total_categories),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "avg_rating": avg_catalog_rating,
        "avg_price": avg_catalog_price,
        "inventory_value": total_inventory_value,
        "top_categories": top_categories,
        "top_products": top_products,
        "has_product_column": first_detected(detected, "product") is not None,
        "has_stock_column": first_detected(detected, "stock") is not None,
    }

    columns = {
        "product": first_detected(detected, "product"),
        "category": first_detected(detected, "category"),
        "stock": first_detected(detected, "stock"),
        "revenue": first_detected(detected, "revenue"),
        "rating": first_detected(detected, "rating"),
        "vendor": first_detected(detected, "vendor"),
    }

    return profile, metrics, columns


def build_sales_profile(df, detected=None):
    """Build sales analytics KPIs and order-level profile from a raw dataset."""
    if detected is None:
        detected = detect_marketplace_columns(df)

    detected = dict(detected)
    detected["revenue"] = _numeric_candidates(df, detected.get("revenue", []))

    order_col = first_detected(detected, "order")
    revenue_col = first_detected(detected, "revenue")
    date_col = first_detected(detected, "date")
    product_col = first_detected(detected, "product")
    category_col = first_detected(detected, "category")
    vendor_col = first_detected(detected, "vendor")
    region_col = first_detected(detected, "region")

    working = df.copy()

    revenue = _numeric_series(working, revenue_col)
    if revenue is None:
        revenue_col = "_transaction_value"
        working[revenue_col] = 1
    else:
        working[revenue_col] = revenue.fillna(0)

    dates = _date_series(working, date_col)
    has_dates = dates is not None and dates.notna().any()
    if has_dates:
        working["_sales_date"] = dates

    total_sales = float(working[revenue_col].sum())

    if order_col:
        total_orders = int(working[order_col].nunique())
    else:
        total_orders = len(working)

    avg_order_value = float(total_sales / total_orders) if total_orders > 0 else 0.0

    def _safe_groupby_sum(col):
        if col and col in working.columns:
            return {str(k): float(v) for k, v in working.groupby(col)[revenue_col].sum().items()}
        return {}

    sales_by_category = _safe_groupby_sum(category_col)
    sales_by_vendor = _safe_groupby_sum(vendor_col)
    sales_by_region = _safe_groupby_sum(region_col)

    top_products = {}
    if product_col and product_col in working.columns:
        top_series = working.groupby(product_col)[revenue_col].sum().nlargest(5)
        
        product_cols = detected.get("product", [])
        label_col = None
        if len(product_cols) > 1:
            for col in product_cols:
                if "name" in str(col).lower() or "title" in str(col).lower():
                    label_col = col
                    break
                    
        if label_col and label_col != product_col:
            mapping = working.drop_duplicates(subset=[product_col]).set_index(product_col)[label_col]
            top_products = {str(mapping.get(k, k)): float(v) for k, v in top_series.items()}
        else:
            top_products = {str(k): float(v) for k, v in top_series.items()}

    top_categories = {}
    if category_col and category_col in working.columns:
        top_categories = {str(k): float(v) for k, v in working.groupby(category_col)[revenue_col].sum().nlargest(5).items()}

    sales_by_date = {}
    growth_pct = 0.0

    if has_dates:
        monthly = working.groupby(working["_sales_date"].dt.to_period("M"))[revenue_col].sum()
        sales_by_date = {str(k): float(v) for k, v in monthly.items()}

        if len(monthly) >= 2:
            monthly_sorted = monthly.sort_index()
            last_month = monthly_sorted.iloc[-1]
            prev_month = monthly_sorted.iloc[-2]
            if prev_month > 0:
                growth_pct = float(((last_month - prev_month) / prev_month) * 100)

    metrics = {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value,
        "sales_by_category": sales_by_category,
        "sales_by_vendor": sales_by_vendor,
        "sales_by_region": sales_by_region,
        "sales_by_date": sales_by_date,
        "top_products": top_products,
        "top_categories": top_categories,
        "growth_pct": growth_pct,
        "has_date_column": has_dates,
    }

    columns = {
        "order": order_col,
        "revenue": revenue_col,
        "date": date_col,
        "product": product_col,
        "category": category_col,
        "vendor": vendor_col,
        "region": region_col,
    }

    if order_col:
        grouped = working.groupby(order_col, dropna=False)
        profile = grouped.agg(revenue=(revenue_col, "sum"))
        if has_dates:
            profile["date"] = grouped["_sales_date"].first()
        profile = profile.reset_index().rename(columns={order_col: "order"})
    else:
        profile = working.copy()
        profile["order"] = profile.index
        profile = profile.rename(columns={revenue_col: "revenue"})
        if has_dates:
            profile["date"] = profile["_sales_date"]

    return profile, metrics, columns


def build_marketplace_profile(df, detected=None):
    """Build marketplace-wide analytics KPIs and a high-level profile from a raw dataset."""
    if detected is None:
        detected = detect_marketplace_columns(df)

    detected = dict(detected)
    detected["revenue"] = _numeric_candidates(df, detected.get("revenue", []))
    detected["rating"] = _numeric_candidates(df, detected.get("rating", []))
    detected["stock"] = _numeric_candidates(df, detected.get("stock", []))

    vendor_col = first_detected(detected, "vendor")
    product_col = first_detected(detected, "product")
    category_col = first_detected(detected, "category")
    order_col = first_detected(detected, "order")
    revenue_col = first_detected(detected, "revenue")
    date_col = first_detected(detected, "date")
    region_col = first_detected(detected, "region")
    rating_col = first_detected(detected, "rating")
    status_col = first_detected(detected, "status")
    stock_col = first_detected(detected, "stock")

    working = df.copy()

    revenue = _numeric_series(working, revenue_col)
    if revenue is None:
        revenue_col = "_transaction_value"
        working[revenue_col] = 1
    else:
        working[revenue_col] = revenue.fillna(0)

    if stock_col:
        stock = _numeric_series(working, stock_col)
        working[stock_col] = stock.fillna(0)

    if rating_col:
        rating = _numeric_series(working, rating_col)
        working[rating_col] = rating.fillna(0)

    total_vendors = int(working[vendor_col].nunique()) if vendor_col else 1
    total_products = int(working[product_col].nunique()) if product_col else 1
    total_categories = int(working[category_col].nunique()) if category_col else 1
    total_revenue = float(working[revenue_col].sum())
    total_orders = int(working[order_col].nunique()) if order_col else len(working)

    avg_vendor_rating = float(working[rating_col].mean()) if rating_col and len(working[rating_col].dropna()) else 0.0

    fulfillment_rate = 0.0
    cancellation_rate = 0.0
    if status_col:
        status_series = working[status_col].astype(str).str.lower()
        success_mask = status_series.str.contains("success|complete|deliver|active|ship", na=False)
        cancel_mask = status_series.str.contains("cancel|return|refund|fail", na=False)
        total = len(status_series)
        if total > 0:
            fulfillment_rate = float((success_mask.sum() / total) * 100)
            cancellation_rate = float((cancel_mask.sum() / total) * 100)

    low_stock_products = 0
    out_of_stock_products = 0
    if stock_col and product_col:
        product_stock = working.groupby(product_col)[stock_col].max()
        out_of_stock_products = int((product_stock <= 0).sum())
        low_stock_products = int(((product_stock > 0) & (product_stock < 10)).sum())
    elif stock_col:
        out_of_stock_products = int((working[stock_col] <= 0).sum())
        low_stock_products = int(((working[stock_col] > 0) & (working[stock_col] < 10)).sum())

    top_vendors = {}
    if vendor_col:
        top_vendors = {str(k): float(v) for k, v in working.groupby(vendor_col)[revenue_col].sum().nlargest(5).items()}

    top_categories = {}
    if category_col:
        top_categories = {str(k): float(v) for k, v in working.groupby(category_col)[revenue_col].sum().nlargest(5).items()}

    top_regions = {}
    if region_col:
        top_regions = {str(k): float(v) for k, v in working.groupby(region_col)[revenue_col].sum().nlargest(5).items()}

    metrics = {
        "total_vendors": total_vendors,
        "total_products": total_products,
        "total_categories": total_categories,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_vendor_rating": avg_vendor_rating,
        "fulfillment_rate": fulfillment_rate,
        "cancellation_rate": cancellation_rate,
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
        "top_vendors": top_vendors,
        "top_categories": top_categories,
        "top_regions": top_regions,
    }

    columns = {
        "vendor": vendor_col,
        "product": product_col,
        "category": category_col,
        "order": order_col,
        "revenue": revenue_col,
        "date": date_col,
        "region": region_col,
        "rating": rating_col,
        "status": status_col,
        "stock": stock_col,
    }

    if vendor_col:
        grouped = working.groupby(vendor_col, dropna=False)
        profile = grouped.agg(revenue=(revenue_col, "sum"))
        if order_col:
            profile["orders"] = grouped[order_col].nunique()
        else:
            profile["orders"] = grouped.size()
        profile = profile.reset_index().rename(columns={vendor_col: "vendor"})
    else:
        profile = working.copy()
        profile["vendor"] = profile.index
        profile = profile.rename(columns={revenue_col: "revenue"})

    return profile, metrics, columns


def build_recommendations(df, detected=None):
    """Generate rule-based recommendations from existing KPIs."""
    if detected is None:
        detected = detect_marketplace_columns(df)
        
    recommendations = []
    
    # Try gathering metrics from existing profiles safely
    mk_metrics = {}
    try:
        _, mk_metrics, _ = build_marketplace_profile(df, detected)
    except Exception:
        pass
        
    cust_metrics = {}
    if first_detected(detected, "customer"):
        try:
            _, cust_metrics, _ = build_customer_profile(df, detected)
        except Exception:
            pass
            
    inv_metrics = {}
    if first_detected(detected, "product"):
        try:
            _, inv_metrics, _ = build_inventory_profile(df, detected)
        except Exception:
            pass
            
    sales_metrics = {}
    try:
        _, sales_metrics, _ = build_sales_profile(df, detected)
    except Exception:
        pass

    # 1. Low stock alert
    low_stock = inv_metrics.get("low_stock_count", mk_metrics.get("low_stock_products", 0))
    if low_stock > 0:
        recommendations.append({
            "title": "Low Stock Warning",
            "priority": "Medium",
            "category": "Inventory",
            "message": f"{low_stock} products are running low on stock.",
            "action": "Review inventory levels and restock top-selling items."
        })
        
    # 2. Out of stock alert
    oos = inv_metrics.get("out_of_stock_count", mk_metrics.get("out_of_stock_products", 0))
    if oos > 0:
        recommendations.append({
            "title": "Out of Stock Alert",
            "priority": "High",
            "category": "Inventory",
            "message": f"{oos} products are completely out of stock.",
            "action": "Contact suppliers immediately to replenish stock."
        })
        
    # 3. Low rating vendors
    avg_rating = mk_metrics.get("avg_vendor_rating", 0.0)
    if 0 < avg_rating < 3.5:
        recommendations.append({
            "title": "Low Vendor Ratings",
            "priority": "High",
            "category": "Quality",
            "message": f"Average vendor rating is low ({avg_rating:.1f}/5.0).",
            "action": "Investigate poor performing vendors and improve quality control."
        })
        
    # 4. Top vendors
    top_vendors = mk_metrics.get("top_vendors", sales_metrics.get("sales_by_vendor", {}))
    if top_vendors:
        best_vendor = list(top_vendors.keys())[0]
        recommendations.append({
            "title": "Top Vendor Performance",
            "priority": "Low",
            "category": "Partnership",
            "message": f"Vendor '{best_vendor}' is leading in revenue.",
            "action": "Establish long-term contracts or feature their products in marketing campaigns."
        })
        
    # 5. Top products
    top_prods = sales_metrics.get("top_products", inv_metrics.get("top_products", {}))
    if top_prods:
        best_prod = list(top_prods.keys())[0]
        recommendations.append({
            "title": "Top Selling Product",
            "priority": "Medium",
            "category": "Sales",
            "message": f"Product '{best_prod}' is a top seller.",
            "action": "Ensure sufficient stock and consider cross-selling opportunities."
        })
        
    # 6. Top categories
    top_cats = mk_metrics.get("top_categories", sales_metrics.get("top_categories", {}))
    if top_cats:
        best_cat = list(top_cats.keys())[0]
        recommendations.append({
            "title": "Leading Category",
            "priority": "Low",
            "category": "Marketing",
            "message": f"Category '{best_cat}' is driving significant revenue.",
            "action": "Allocate more marketing budget to this category."
        })
        
    # 7. High revenue segments
    segments = cust_metrics.get("segments", {})
    if segments:
        champions = segments.get("Champions", 0)
        if champions > 0:
            recommendations.append({
                "title": "High Value Customers",
                "priority": "Medium",
                "category": "Retention",
                "message": f"You have {champions} 'Champion' customers.",
                "action": "Create an exclusive VIP program to reward loyalty."
            })
            
    # 8. Poor fulfillment
    fulfillment = mk_metrics.get("fulfillment_rate", 0.0)
    if 0 < fulfillment < 85.0:
        recommendations.append({
            "title": "Fulfillment Issues",
            "priority": "High",
            "category": "Operations",
            "message": f"Fulfillment rate is concerningly low at {fulfillment:.1f}%.",
            "action": "Audit logistics partners and shipping workflows."
        })
        
    # 9. High cancellation
    cancellation = mk_metrics.get("cancellation_rate", 0.0)
    if cancellation > 10.0:
        recommendations.append({
            "title": "High Cancellation Rate",
            "priority": "High",
            "category": "Operations",
            "message": f"Order cancellation rate is {cancellation:.1f}%.",
            "action": "Review product descriptions and inventory accuracy to prevent false orders."
        })
        
    # 10. Regional opportunity
    top_regions = mk_metrics.get("top_regions", sales_metrics.get("sales_by_region", {}))
    if top_regions:
        best_region = list(top_regions.keys())[0]
        recommendations.append({
            "title": "Regional Growth",
            "priority": "Medium",
            "category": "Expansion",
            "message": f"Region '{best_region}' is showing strong sales.",
            "action": "Consider localized marketing or opening a local fulfillment center."
        })
        
    # 11. Customer retention opportunity
    repeat_rate = cust_metrics.get("repeat_rate", 0.0)
    if 0 < repeat_rate < 30.0:
        recommendations.append({
            "title": "Low Customer Retention",
            "priority": "High",
            "category": "Marketing",
            "message": f"Only {repeat_rate:.1f}% of customers make repeat purchases.",
            "action": "Launch targeted email campaigns and a loyalty rewards program."
        })
        
    # 12. Revenue growth opportunity
    growth = sales_metrics.get("growth_pct", 0.0)
    has_date = sales_metrics.get("has_date_column", False)
    if has_date and growth < 0:
        recommendations.append({
            "title": "Negative Revenue Growth",
            "priority": "High",
            "category": "Strategy",
            "message": f"Revenue has declined by {abs(growth):.1f}% recently.",
            "action": "Analyze recent market changes, review pricing, and launch promotional campaigns."
        })
    elif has_date and growth > 15:
        recommendations.append({
            "title": "Strong Revenue Growth",
            "priority": "Low",
            "category": "Strategy",
            "message": f"Revenue is growing rapidly at {growth:.1f}%.",
            "action": "Capitalize on momentum by scaling up successful ad campaigns."
        })

    summary = {
        "total_recommendations": len(recommendations),
        "high_priority_count": sum(1 for r in recommendations if r["priority"] == "High"),
        "medium_priority_count": sum(1 for r in recommendations if r["priority"] == "Medium"),
        "low_priority_count": sum(1 for r in recommendations if r["priority"] == "Low"),
    }
    
    return recommendations, summary
