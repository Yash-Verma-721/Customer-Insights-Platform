import time
import re
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.customer_metrics import (
    build_customer_profile,
    customer_recommendations,
    detect_customer_columns,
    money,
    percent,
)
from utils.ui_helpers import (
    add_session_log,
    branded_spinner,
    calculate_readiness_score,
    render_empty_state,
    render_footer,
    render_header,
    render_help_expander,
)
from utils.data_source_helper import get_analytics_df, render_data_source_banner
from utils.ui_components import (
    page_wrapper, page_header, section_header,
    kpi_card, info_card, render_metric_tile,
    bento_card, ranking_card, chart_container,
    render_page_header, render_section_header,
    render_kpi_card, render_info_card, render_ranking_list
)
from utils.ui_constants import *

CUSTOMER_RULES = {
    "NON_ADDITIVE_KEYWORDS": ["age", "ages", "rating", "ratings", "review", "reviews", "satisfaction", "score", "scores", "percent", "percentage", "percentages", "pct", "rate", "rates", "discount", "discounts", "nps", "sentiment", "risk", "risks"],
    "VALUE_KEYWORDS": ["sale", "sales", "revenue", "revenues", "price", "prices", "amount", "amounts", "cost", "costs", "margin", "margins", "qty", "quantity", "quantities", "profit", "profits", "purchase", "purchases", "income", "incomes", "page", "pages", "visit", "visits", "visited", "lifetime", "value", "values", "spend", "spending", "spent"],
    "IDENTIFIER_KEYWORDS": ["id", "ids", "zip", "zips", "code", "codes", "serial", "serials", "number", "numbers", "num", "nums", "record", "records", "identifier", "identifiers", "customer_id"]
}

def _is_vis_technical_identifier(column):
    norm = str(column).strip().lower().replace(" ", "_").replace("-", "_")
    if norm in {"id", "index", "serial", "uuid", "guid", "hash", "transaction_id", "invoice_id", "order_id", "phone", "mobile"} or norm.endswith("_id"): return True
    return any(ex in norm for ex in ["description", "remark", "comment", "note", "address", "email", "contact"])

def _get_count_label(dimension, detected_columns=None):
    if not dimension: return "Records"
    norm = str(dimension).lower()
    for keys, label in {("customer", "client", "user", "buyer"): "Customers", ("product", "item", "sku"): "Products", ("order",): "Orders", ("invoice",): "Invoices", ("transaction",): "Transactions", ("employee",): "Employees", ("ticket",): "Tickets"}.items():
        if any(k in norm for k in keys): return label
    if detected_columns:
        if detected_columns.get("order"): return "Orders"
        if detected_columns.get("customer"): return "Customers"
    return "Records"

def _has_keyword(text, keywords):
    """Safely matches any keyword in the text using word boundaries."""
    if not text: return False
    text_norm = str(text).lower().replace("_", " ").replace("-", " ")
    return any(re.search(rf'\b{re.escape(str(k).lower().replace("_", " ").replace("-", " "))}\b', text_norm) for k in keywords)

def _evaluate_customer_logic(df, dimension, metric, agg_func):
    if agg_func == "Count" or not metric: return "Recommended", "", "", ""
    if _has_keyword(metric, CUSTOMER_RULES["NON_ADDITIVE_KEYWORDS"]):
        return ("Not Recommended", f"Summing '{metric}' combines unrelated values and does not produce a meaningful customer metric.", f"Use Average to compare '{metric}' across {dimension}.", f"Although mathematically correct, this metric generally has limited customer interpretation because '{metric}' is usually analyzed using averages or distributions rather than totals.") if agg_func == "Sum" else ("Acceptable", "", "", "")
    if _has_keyword(metric, CUSTOMER_RULES["IDENTIFIER_KEYWORDS"]) and agg_func in ["Sum", "Average"]:
        return ("Not Recommended", f"Mathematical operations like {agg_func} on identifier fields ('{metric}') are usually invalid.", f"Use Count to measure the number of records across {dimension}.", "Mathematical operations on identifiers provide no customer value.")
    if _has_keyword(metric, CUSTOMER_RULES["VALUE_KEYWORDS"]) and agg_func in ["Sum", "Average"]:
        return "Recommended", "This is a meaningful customer comparison.", "", ""
    if pd.api.types.is_numeric_dtype(df[metric]):
        temp = df[metric].dropna()
        if not temp.empty and ((0 <= temp.min() and temp.max() <= 10) or (0 <= temp.min() and temp.max() <= 100 and temp.max() > 15)) and agg_func == "Sum":
            return ("Acceptable", f"This metric's distribution resembles a score or rate. While mathematically correct, ensure that summing these values across {dimension} aligns with your customer logic.", "", "This chart aggregates a metric that statistically behaves like a rate or score.")
    return "Acceptable", "The customer meaning of this metric could not be confidently identified. Please interpret the results based on your dataset context.", "", ""

def _process_chart_data(df, chart_type, x_axis, y_axis, agg_func, top_n_val):
    start_time = time.time()
    if chart_type in ["Scatter Plot", "Box Plot", "Histogram"]:
        sampled = len(df) > 5000
        processed_df = df.sample(n=5000, random_state=42) if sampled else df.copy()
        return processed_df, len(df), len(processed_df), sampled, time.time() - start_time
        
    agg_map = {"Sum": "sum", "Average": "mean", "Maximum": "max", "Minimum": "min"}
    grouped = df.groupby(x_axis, as_index=False)[y_axis].size().rename(columns={"size": y_axis}) if agg_func == "Count" else df.groupby(x_axis, as_index=False)[y_axis].agg(agg_map[agg_func])
    grouped = grouped.sort_values(y_axis, ascending=False)
    
    limit, include_others = len(grouped), False
    if top_n_val == "Auto (Recommended)":
        if chart_type == "Pie Chart": limit, include_others = 10, True
        elif chart_type == "Bar Chart": limit = 20
    else:
        limit_str = ''.join(filter(str.isdigit, str(top_n_val)))
        if limit_str: limit = int(limit_str)
        include_others = "+ Others" in str(top_n_val)

    grouped_others = False
    if len(grouped) > limit:
        processed_df = grouped.head(limit)
        if include_others:
            others_row = pd.DataFrame({x_axis: [f"Others (Remaining {len(grouped) - limit})"], y_axis: [grouped.iloc[limit:][y_axis].agg(agg_map.get(agg_func, "sum"))]})
            processed_df = pd.concat([processed_df, others_row], ignore_index=True)
            grouped_others = True
    else:
        processed_df = grouped
        
    if chart_type in ["Line Chart", "Area Chart"]: processed_df = processed_df.sort_values(x_axis)
    return processed_df, len(df), len(processed_df), grouped_others, time.time() - start_time

def _top_group(df, dimension, metric=None, top_n=10):
    if not dimension: return pd.DataFrame(), ""
    if metric and pd.api.types.is_numeric_dtype(pd.to_numeric(df[metric], errors="coerce")):
        temp = df.copy()
        temp[metric] = pd.to_numeric(temp[metric], errors="coerce").fillna(0)
        grouped = temp.groupby(dimension, dropna=False)[metric].sum().reset_index()
        y_label = metric
    else:
        grouped = df[dimension].value_counts(dropna=False).reset_index()
        grouped.columns = [dimension, "Count"]
        y_label = "Count"
    return grouped.sort_values(y_label, ascending=False).head(top_n), y_label

def _apply_chart_layout(fig, height=320, t=15, b=15):
    """Centralized chart styling."""
    fig.update_layout(height=height, margin=dict(l=15, r=15, t=t, b=b))
    return fig

def _render_ml_segmentation():
    from utils.ml_models import (
        get_ml_customer_clusters, 
        get_ml_customer_summary, 
        get_ml_customer_metrics, 
        get_ml_customer_recommendations
    )
    
    with chart_container("ML Customer Segmentation & Clustering"):
        metrics = get_ml_customer_metrics()
        
        if not metrics or metrics.get("status") != "success":
            render_info_card("ML Segmentation Status", "ML Customer Segmentation is unavailable for the current dataset.", ICON_AI, "info")
            return
            
        c_df = get_ml_customer_clusters()
        summ = get_ml_customer_summary()
        recs = get_ml_customer_recommendations()
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Segments", metrics.get("cluster_count", 0))
        k2.metric("Optimal K", metrics.get("optimal_k", "N/A"))
        k3.metric("Silhouette Score", f"{metrics.get('silhouette_score', 0):.3f}")
        k4.metric("Customers Clustered", f"{metrics.get('total_customers', 0):,}")
        
        fig1 = px.bar(summ, x="ml_segment", y="customer_count", text_auto=True, title="Customer Count per Segment")
        st.plotly_chart(_apply_chart_layout(fig1, height=300), use_container_width=True)

def _render_custom_explorer(df, detected):
    vis_cols = [c for c in df.columns if not _is_vis_technical_identifier(c) and df[c].dropna().nunique() > 0] or df.columns.tolist()
    met_cols = df[vis_cols].select_dtypes(include="number").columns.tolist()
    priority_keys = ["product", "category", "sub category", "brand", "customer", "supplier", "region", "country", "state", "city", "status", "channel", "payment", "month", "quarter", "year"]
    dim_cols = sorted([c for c in vis_cols if c not in met_cols], key=lambda c: next((i for i, k in enumerate(priority_keys) if k in str(c).lower()), 999))
    
    for k, v in {"ce_mode": "Quick", "ce_chart": "Bar Chart", "ce_generated": False}.items(): st.session_state.setdefault(k, v)

    mode = st.radio("Mode", ["Quick", "Advanced"], horizontal=True, key="ce_mode")
    with st.expander("ℹ️ How Quick Mode Works" if mode == "Quick" else "ℹ️ Advanced Controls Guide"):
        st.markdown("""
        Quick Mode automatically applies Customer Intelligence best practices to your charts:
        - **Pie Chart**: Displays the Top 10 categories + groups the rest into "Others" (for a complete 100% distribution).
        - **Bar Chart**: Displays the Top 20 categories to keep comparisons clean and readable.
        - **Line / Area Chart**: Aggregates the full timeline trend.
        - **Histogram**: Displays raw numeric distribution.
        - **Scatter / Box Plot**: Automatically applies row sampling (max 5,000 rows) for fast performance.
        """ if mode == "Quick" else """
        - **Aggregation**: Defines how multiple records are combined (Sum, Count, Average, etc.).
        - **Top N**: Shows only the top-ranking categories. (e.g., "Top 10" ignores the remaining data).
        - **Top N + Others**: Shows the top-ranking categories and merges everything else into a single "Others" group to represent the complete dataset.
        - **Auto (Recommended)**: The system decides the best performance limits based on the selected Chart Type.
        """)
        
    try:
        cont_config = st.container(border=True)
    except TypeError:
        cont_config = st.container()
        
    with cont_config:
        c1, c2, c3 = st.columns(3)
        chart_type = c1.selectbox("Chart Type", ["Bar Chart", "Line Chart", "Area Chart", "Scatter Plot", "Box Plot", "Histogram", "Pie Chart"], key="ce_chart")
        
        x_label, y_label, x_opts, y_opts = ("X Metric", "Y Metric", met_cols, met_cols) if chart_type == "Scatter Plot" else ("Numeric Field", "Metric", met_cols, []) if chart_type == "Histogram" else ("Grouping Dimension (Optional)", "Numeric Metric", ["None"] + dim_cols, met_cols) if chart_type == "Box Plot" else ("Dimension", "Metric", dim_cols, met_cols)

        x_val, y_val = st.session_state.get("ce_x"), st.session_state.get("ce_y")
        x_axis = c2.selectbox(x_label, x_opts, index=x_opts.index(x_val) if x_opts and x_val in x_opts else 0, key="ce_x") if x_opts else None
        
        is_count = mode == "Advanced" and st.session_state.get("ce_agg") == "Count" and chart_type not in ["Scatter Plot", "Histogram"]
        if is_count: c3.selectbox(y_label, ["Not Required for Count"], disabled=True)
        actual_y = met_cols[0] if met_cols and is_count else (c3.selectbox(y_label, y_opts, index=y_opts.index(y_val) if y_opts and y_val in y_opts else (1 if chart_type == "Scatter Plot" and len(met_cols) > 1 else 0), key="ce_y") if y_opts else None)
        actual_x = None if x_axis == "None" else x_axis

        if mode == "Advanced":
            c4, c5, _ = st.columns(3)
            agg_func = c4.selectbox("Aggregation", ["Sum", "Count", "Average", "Maximum", "Minimum"], key="ce_agg")
            opts = ["Top 5", "Top 10", "Top 20", "Top 30", "Top 5 + Others", "Top 10 + Others", "Top 20 + Others", "Auto (Recommended)"]
            top_n_val = c5.selectbox("Top N Limit", opts, index=opts.index(st.session_state.get("ce_topn")) if st.session_state.get("ce_topn") in opts else 7, key="ce_topn")
            c5.caption("Includes all data (others grouped)." if "Others" in top_n_val or (top_n_val == "Auto (Recommended)" and chart_type == "Pie Chart") else "Shows all chronological data." if top_n_val == "Auto (Recommended)" and chart_type in ["Line Chart", "Area Chart"] else "Filters data (others excluded).")
        else:
            agg_func, top_n_val = "Count" if actual_y and _has_keyword(actual_y, CUSTOMER_RULES["IDENTIFIER_KEYWORDS"]) else "Average" if actual_y and _has_keyword(actual_y, CUSTOMER_RULES["NON_ADDITIVE_KEYWORDS"]) else "Sum", "Auto (Recommended)"

    exps = {
        "Bar Chart": "**Bar Chart**: Best for comparing categorical data (e.g., Sales by Region).",
        "Pie Chart": "**Pie Chart**: Best for showing market share or parts of a whole.",
        "Line Chart": "**Line Chart**: Best for visualizing trends over time.",
        "Area Chart": "**Area Chart**: Similar to a Line Chart, but emphasizes total magnitude.",
        "Scatter Plot": "**Scatter Plot**: Best for finding correlations between two numeric metrics.",
        "Box Plot": "**Box Plot**: Best for understanding statistical distributions and outliers.",
        "Histogram": "**Histogram**: Best for viewing frequency distribution of a single numeric field."
    }

    caveat = ""
    if actual_x and actual_y:
        x_is_num, y_is_num, x_is_date = actual_x in met_cols, actual_y in met_cols, pd.api.types.is_datetime64_any_dtype(df[actual_x]) or 'date' in str(actual_x).lower()
        rec = "Scatter Plot to find correlations between numeric variables." if x_is_num and y_is_num and chart_type != "Scatter Plot" else "Line Chart to track trends over time." if x_is_date and chart_type not in ["Line Chart", "Area Chart"] else "Pie Chart to view distribution share among these few categories." if not x_is_num and df[actual_x].nunique() <= 10 and chart_type != "Pie Chart" else "Bar Chart to compare metrics across many categories." if not x_is_num and df[actual_x].nunique() > 10 and chart_type not in ["Bar Chart", "Line Chart", "Area Chart"] else None
        if rec and mode == "Quick": st.success(f"💡 **Dynamic Suggestion:** Try a **{rec}** based on your selected data.")

        status, reason, suggestion, caveat = _evaluate_customer_logic(df, actual_x, actual_y, agg_func)
        if status == "Recommended" and reason: st.success(f"🟢 **Recommended:** {reason}")
        elif status == "Acceptable" and reason: st.warning(f"🟡 **Acceptable:** {reason}")
        elif status == "Not Recommended": st.error(f"🔴 **Not Recommended**\n\n**Reason:** {reason}\n\n**Suggested Alternative:** {suggestion}")

    st.markdown("---")
    if st.columns([1, 4])[0].button("Generate Visualization", type="primary"): st.session_state.ce_generated = True

    if not st.session_state.ce_generated:
        st.markdown("<div style='padding: 25px; text-align: center; background-color: #f8f9fa; border-radius: 8px; border: 1px dashed #ced4da;'><h3 style='color: #495057; margin-bottom: 12px;'>📊 Visualization Preview</h3><p style='color: #6c757d; font-size: 16px;'>Select your Chart Type and Metrics above, then click <b>Generate Visualization</b>.</p></div>", unsafe_allow_html=True)
    else:
        _render_custom_chart(df, chart_type, actual_x, actual_y, agg_func, top_n_val, dim_cols, met_cols, detected, exps, caveat)

def _render_custom_chart(df, chart_type, x_axis, y_axis, agg_func, top_n_val, dim_cols, met_cols, detected, exps, caveat):
    msg, rec_msg = "", ""
    if chart_type in ["Pie Chart", "Bar Chart", "Line Chart", "Area Chart"]:
        if x_axis not in dim_cols: msg, rec_msg = f"{chart_type} requires a Categorical or Date Dimension.", "Please select a valid Dimension, or switch to a Scatter Plot."
        elif not y_axis: msg = f"{chart_type} requires a numeric Metric."
    elif chart_type == "Histogram" and x_axis not in met_cols: msg = "Histogram requires a numeric Metric."
    elif chart_type == "Scatter Plot" and (x_axis not in met_cols or y_axis not in met_cols): msg, rec_msg = "Scatter Plot requires both X and Y to be numeric metrics.", "Please select two Metrics, or switch to a Bar Chart."
    elif chart_type == "Box Plot" and not y_axis: msg = "Box Plot requires a numeric Metric."

    if msg:
        st.error(f"Invalid Configuration: {msg}")
        if rec_msg: st.warning(rec_msg)
        return

    with branded_spinner("Processing data..."):
        from utils.cache import get_cached_metric
        plot_df, total_recs, disp_cats, has_others, p_time = get_cached_metric(f"chart_{chart_type}_{x_axis}_{y_axis}_{agg_func}_{top_n_val}", _process_chart_data, df, chart_type, x_axis, y_axis, agg_func, top_n_val)

    disp_lbl = {"Count": _get_count_label(x_axis, detected), "Sum": f"Total {y_axis}", "Average": f"Average {y_axis}", "Maximum": f"Maximum {y_axis}", "Minimum": f"Minimum {y_axis}"}.get(agg_func, y_axis)

    chart_funcs = {
        "Bar Chart": lambda: px.bar(plot_df, x=x_axis, y=y_axis, labels={y_axis: disp_lbl}),
        "Line Chart": lambda: px.line(plot_df, x=x_axis, y=y_axis, labels={y_axis: disp_lbl}),
        "Area Chart": lambda: px.area(plot_df, x=x_axis, y=y_axis, labels={y_axis: disp_lbl}),
        "Scatter Plot": lambda: px.scatter(plot_df, x=x_axis, y=y_axis, labels={y_axis: disp_lbl}),
        "Box Plot": lambda: px.box(plot_df, x=x_axis, y=y_axis, labels={y_axis: disp_lbl}),
        "Pie Chart": lambda: px.pie(plot_df, names=x_axis, values=y_axis, labels={y_axis: disp_lbl}),
        "Histogram": lambda: px.histogram(plot_df, x=x_axis)
    }
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Chart Type", chart_type)
    s2.metric("Aggregation", "Raw/Sampled" if chart_type in ["Scatter Plot", "Box Plot", "Histogram"] else agg_func)
    s3.metric("Processed Records", f"{total_recs:,}")
    s4.metric("Displayed Categories", f"{disp_cats} (incl. Others)" if has_others and chart_type not in ["Scatter Plot", "Box Plot", "Histogram"] else f"{disp_cats}")

    st.plotly_chart(_apply_chart_layout(chart_funcs[chart_type](), height=420, t=25, b=25), use_container_width=True)

    if chart_type in ["Scatter Plot", "Box Plot", "Histogram"] and has_others: st.caption("ℹ️ Showing a randomly sampled dataset (5,000 records) for better performance.")

    st.caption(f"⏱️ Processing Time: {p_time:.3f} seconds")
    st.download_button(label="📥 Download Processed Data (CSV)", data=plot_df.to_csv(index=False).encode('utf-8'), file_name=f"visualization_{chart_type.replace(' ', '_').lower()}.csv", mime="text/csv")
    add_session_log(f"Generated enterprise chart: {chart_type}")

def show_customer_analytics():
    with page_wrapper():
        df, source_label, source_name = get_analytics_df("customer")

        # ---------------- Tier 1: Executive Header ---------------- #
        page_header(
            title="Customer Analytics",
            subtitle=f"Active Dataset: {source_name or 'Customer Base'} | Access Level: Executive",
            status="Nominal",
            status_type="success"
        )
        render_data_source_banner(source_label, source_name)

        if df is None or df.empty:
            render_empty_state()
            render_footer("Customer Analytics")
            return

        with branded_spinner("Loading visualization analytics..."):
            from utils.cache import get_cached_metric
            detected = get_cached_metric("detected", detect_customer_columns, df)
            profile, metrics, columns = get_cached_metric("profile", build_customer_profile, df, detected)

        # ---------------- Tier 2: Quick KPI Grid ---------------- #
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            render_kpi_card(
                "Total Customers",
                f"{metrics.get('total_customers', 0):,}",
                "Customer Base",
                "up",
                ICON_CUSTOMER
            )

        with k2:
            render_kpi_card(
                "Customer Revenue",
                money(metrics.get("total_revenue", 0)),
                "Total Lifetime Sales",
                "up",
                ICON_SALES
            )

        with k3:
            render_kpi_card(
                "Repeat Purchase Rate",
                percent(metrics.get("repeat_rate", 0)),
                "Retention Health",
                "up",
                ICON_TREND_UP
            )

        with k4:
            render_kpi_card(
                "Avg Order Value",
                money(metrics.get("avg_order_value", 0)),
                "Order Economics",
                "up",
                ICON_SALES
            )

        # ---------------- Tier 3: Primary Analytics Grid (Responsive 2:1 Bento Layout) ---------------- #
        bento_left, bento_right = st.columns([2, 1])

        with bento_left:
            with chart_container("Customer RFM Segments", subtitle="Customer distribution by RFM behavioral tiers"):
                segment_df = profile["segment"].value_counts().rename_axis("Segment").reset_index(name="Customers")
                fig_seg = px.bar(segment_df, x="Segment", y="Customers", text_auto=True)
                st.plotly_chart(_apply_chart_layout(fig_seg, height=320), use_container_width=True)

        with bento_right:
            with bento_card("Customer Summary", ICON_CUSTOMER):
                render_metric_tile("Purchase Frequency", f"{metrics.get('purchase_frequency', 0):.2f}x")
                render_metric_tile("One-Time Customers", f"{metrics.get('one_time_customers', 0):,}")
                render_metric_tile("Top 10% Revenue Share", percent(metrics.get("top_10_revenue_share", 0)), metrics.get("top_10_revenue_share", 0))

            if not segment_df.empty:
                top_seg = segment_df.iloc[0]['Segment']
                top_cnt = segment_df.iloc[0]['Customers']
                with bento_card("Customer Leaders", ICON_TREND_UP):
                    render_ranking_list([
                        {"name": str(top_seg), "value": f"🥇 Top Segment ({top_cnt:,} customers)"}
                    ])

        # ---------------- Tier 4: Secondary Analytics Grid (50% / 50%) ---------------- #
        sec1, sec2 = st.columns(2)

        with sec1:
            with chart_container("Retention & Churn-Risk Signals", subtitle="Key retention indicators and at-risk account follow-up"):
                at_risk = profile[profile["segment"].isin(["At Risk", "One-Time Customers", "Needs Attention"])]
                r1, r2 = st.columns(2)
                r1.metric("One-Time Buyers", f"{len(profile[profile['frequency'] == 1]):,}")
                r2.metric("At-Risk Accounts", f"{len(at_risk):,}")
                st.dataframe(at_risk.sort_values(["monetary", "frequency"], ascending=False).head(30), use_container_width=True, hide_index=True)

        with sec2:
            if columns.get("region"):
                with chart_container("Regional Customer Distribution", subtitle="Revenue concentration by geographic region"):
                    grouped, y_label = _top_group(df, columns["region"], columns["revenue"], top_n=15)
                    st.plotly_chart(_apply_chart_layout(px.bar(grouped, x=columns["region"], y=y_label, text_auto=".2s"), height=250), use_container_width=True)
            else:
                with chart_container("Customer Profile Overview", subtitle="RFM score breakdown"):
                    st.dataframe(profile.sort_values(["rfm_score", "monetary"], ascending=False).head(50), use_container_width=True, hide_index=True)

        # ML Segmentation Section (if available)
        from utils.ml_models import get_ml_customer_metrics
        has_ml = get_ml_customer_metrics() and get_ml_customer_metrics().get("status") == "success"
        if has_ml:
            _render_ml_segmentation()

        # ---------------- Tier 5: Customer Intelligence & AI Recommendations ---------------- #
        section_header("Customer Intelligence & AI Insights", subtitle="Retention signals, churn risk analysis, and strategic marketing advice")

        bot1, bot2 = st.columns(2)

        with bot1:
            with chart_container("Customer Alerts & Risk Feed"):
                one_time_count = len(profile[profile['frequency'] == 1])
                if one_time_count > 0:
                    render_info_card("One-Time Customer Risk", f"{one_time_count:,} customers have made only 1 purchase.", ICON_ALERT, "warning")
                
                at_risk_count = len(profile[profile["segment"].isin(["At Risk", "Needs Attention"])])
                if at_risk_count > 0:
                    render_info_card("Churn Warning", f"{at_risk_count:,} accounts identified in At-Risk / Needs Attention segments.", ICON_ALERT, "danger")

                if metrics.get("repeat_rate", 0) > 20:
                    render_info_card("Healthy Retention", f"Repeat purchase rate is strong at {percent(metrics.get('repeat_rate', 0))}.", ICON_SUCCESS, "success")

        with bot2:
            with chart_container("Strategic Customer Recommendations"):
                recs = customer_recommendations(metrics)
                if not recs:
                    render_info_card("Recommendations", "Customer profile metrics indicate nominal performance.", ICON_AI, "info")
                else:
                    for rec in recs[:3]:
                        render_info_card("Customer Insight", rec, ICON_AI, "info")

        # Custom Chart Builder & Explorer
        with chart_container("Custom Customer Chart Builder & Data Explorer"):
            _render_custom_explorer(df, detected)

        # Detailed Customer Report Generator
        with chart_container("Detailed Customer Report Generator"):
            with st.expander("Customer Intelligence Glossary"):
                st.markdown(
                    """
                    - **Repeat Purchase Rate**: Share of customers with more than one transaction.
                    - **Purchase Frequency**: Average number of records or orders per customer.
                    - **Top 10% Revenue Share**: Revenue concentration among the highest-value customers.
                    - **RFM Score**: Combined recency, frequency, and monetary score used for segmentation.
                    - **One-Time Customers**: Customers with only one recorded transaction.
                    """
                )

            st.markdown("---")
            st.markdown("**📄 Generate Customer Analytics Report**")
            if st.button("Generate Customer Report", type="primary"):
                with branded_spinner("Generating Customer Report..."):
                    from modules.reports.customer_report import build_customer_report_blocks
                    from modules.reports.report_utils import generate_excel_bytes
                    from utils.ml_models import get_ml_customer_metrics, get_ml_customer_summary

                    ml_metrics = get_ml_customer_metrics()
                    ml_summ = get_ml_customer_summary()

                    blocks = build_customer_report_blocks(metrics, ml_metrics, ml_summ)
                    st.session_state["customer_report_bytes"] = generate_excel_bytes(blocks, "Customer Report")

            if "customer_report_bytes" in st.session_state:
                st.download_button(
                    label="Download Customer Report",
                    data=st.session_state["customer_report_bytes"],
                    file_name="customer_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="secondary"
                )

        render_footer("Customer Analytics")
