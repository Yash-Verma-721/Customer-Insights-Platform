import streamlit as st
import pandas as pd
import plotly.express as px

from utils.ui_helpers import (
    render_header, render_empty_state, render_help_expander, 
    render_footer, add_session_log, branded_spinner
)
from modules.analytics_customer import CUSTOMER_RULES
from utils.cache import get_cached_metric
from utils.data_source_helper import get_analytics_df, render_data_source_banner

# ==========================================
# 1. Constants
# ==========================================

IDENTIFIER_NAMES = {
    "index", "id", "row", "rowid", "row_id", "row_number", "rownumber",
    "serial", "serial_no", "serialnumber", "sno", "s_no", "sr_no", "srno",
    "unnamed_0", "unnamed:0", "uuid", "timestamp_id", "timestamp_ids"
}

BUSINESS_DIMENSIONS = {
    "product", "brand", "category", "sub_category", "subcategory",
    "customer_segment", "region", "country", "city", "status",
    "payment_mode", "channel", "department"
}

BUSINESS_METRIC_HINTS = {
    "amount", "price", "revenue", "sales", "profit", "cost", "value",
    "quantity", "qty", "discount", "rating", "score", "count", "total",
    "order", "purchase", "spend", "income", "margin", "age", "tenure"
}

TEXT_FIELD_HINTS = {
    "description", "review", "comment", "comments", "feedback", "message",
    "notes", "note", "summary", "title", "text", "details"
}

# ==========================================
# 2. Small utility/helper functions
# ==========================================

def _normalize_column_name(column):
    return str(column).strip().lower().replace(" ", "_").replace("-", "_")

def _is_business_dimension(column):
    normalized = _normalize_column_name(column)
    return any(dim in normalized for dim in BUSINESS_DIMENSIONS)

def _display_column_name(column):
    return str(column).replace("_", " ").strip().title()

def _is_identifier_name(column):
    normalized = _normalize_column_name(column)
    return (
        normalized in IDENTIFIER_NAMES
        or normalized.endswith("_id")
        or normalized.startswith("id_")
        or normalized.startswith("unnamed")
    )

def _is_sequence_like(series):
    numeric = pd.to_numeric(series.dropna(), errors="coerce").dropna()
    if len(numeric) < 3 or numeric.nunique() != len(numeric):
        return False
    sorted_values = numeric.sort_values().reset_index(drop=True)
    diffs = sorted_values.diff().dropna()
    return len(diffs) > 0 and diffs.nunique() == 1 and diffs.iloc[0] in (1, 1.0)

def _is_business_metric(column):
    normalized = _normalize_column_name(column)
    return any(hint in normalized for hint in BUSINESS_METRIC_HINTS)

def _is_free_text_field(column):
    normalized = _normalize_column_name(column)
    return any(hint in normalized for hint in TEXT_FIELD_HINTS)

def _split_numeric_columns(df):
    useful_cols = []
    excluded_cols = []
    row_count = len(df)

    for column in df.select_dtypes(include="number").columns:
        norm_col = _normalize_column_name(column)
        if any(d in norm_col for d in ["time", "timestamp"]):
            excluded_cols.append(column)
            continue
            
        series = df[column]
        unique_count = series.dropna().nunique()
        ratio = unique_count / row_count if row_count > 0 else 0
        
        is_named_identifier = _is_identifier_name(column)
        is_sequence_identifier = _is_sequence_like(series)
        has_variation = unique_count > 1
        is_business_dim = _is_business_dimension(column)
        
        if is_business_dim:
            if ratio > 0.95:
                is_named_identifier = True
            else:
                is_named_identifier = False
                is_sequence_identifier = False

        if has_variation and not is_named_identifier and (not is_sequence_identifier or _is_business_metric(column)):
            useful_cols.append(column)
        else:
            excluded_cols.append(column)

    return useful_cols, excluded_cols

def _split_segment_columns(df):
    useful_cols = []
    excluded_cols = []
    row_count = len(df)

    for column in df.select_dtypes(include=["object", "string", "category", "datetime"]).columns:
        norm_col = _normalize_column_name(column)
        if any(d in norm_col for d in ["date", "time", "timestamp", "year", "month", "day"]):
            excluded_cols.append(column)
            continue
            
        unique_count = df[column].dropna().nunique()
        ratio = unique_count / row_count if row_count > 0 else 0
        
        is_business_dim = _is_business_dimension(column)
        is_named_identifier = _is_identifier_name(column)
        
        if is_business_dim:
            if ratio > 0.95:
                too_sparse = True
                is_named_identifier = True
            else:
                too_sparse = False
                is_named_identifier = False
        else:
            too_sparse = row_count > 0 and unique_count > max(50, row_count * 0.7)

        if 1 < unique_count and not too_sparse and not is_named_identifier and not _is_free_text_field(column):
            useful_cols.append(column)
        else:
            excluded_cols.append(column)

    return useful_cols, excluded_cols

def _format_number(value):
    if pd.isna(value):
        return "0.00"
    return f"{value:,.2f}"

def _metric_summary(series):
    data = pd.to_numeric(series, errors="coerce").dropna()
    if data.empty:
        return None
    return {
        "average": data.mean(),
        "median": data.median(),
        "maximum": data.max(),
        "minimum": data.min(),
        "std": data.std(),
        "p75": data.quantile(0.75),
        "p90": data.quantile(0.90),
    }

def _build_segment_table(df, segment_col, metric_col=None):
    grouped = (
        df[segment_col]
        .value_counts(dropna=False)
        .rename_axis(segment_col)
        .reset_index(name="Records")
    )
    total_records = grouped["Records"].sum()
    grouped["Share"] = grouped["Records"] / total_records if total_records else 0

    if metric_col:
        metric_data = df.copy()
        metric_data[metric_col] = pd.to_numeric(metric_data[metric_col], errors="coerce")
        metric_grouped = (
            metric_data.groupby(segment_col, dropna=False)[metric_col]
            .agg(["sum", "mean"])
            .reset_index()
            .rename(columns={"sum": "Total Value", "mean": "Avg Value"})
        )
        grouped = grouped.merge(metric_grouped, on=segment_col, how="left")

    grouped["Share"] = grouped["Share"].map(lambda value: f"{value:.1%}")
    return grouped

# ==========================================
# 3. Rendering helpers
# ==========================================

def _render_metric_card(title, tooltip, value):
    st.markdown(f"""
        <div class="stCard">
            <div class="metric-title-container" data-tooltip="{tooltip}">
                <div class="metric-card-title">{title}</div>
            </div>
            <div class="metric-card-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)


def _render_segment_overview(segment_table, selected_cat, selected_metric, segment_name, metric_name, segment_count):
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Segments", f"{segment_count:,}")
    
    if selected_metric:
        is_non_additive = any(k in str(selected_metric).lower() for k in CUSTOMER_RULES["NON_ADDITIVE_KEYWORDS"])
        sorted_by_total = segment_table.sort_values("Total Value", ascending=False)
        sorted_by_avg = segment_table.sort_values("Avg Value", ascending=False)
        
        top_total_segment = sorted_by_total.iloc[0][selected_cat] if not sorted_by_total.empty else "N/A"
        top_avg_segment = sorted_by_avg.iloc[0][selected_cat] if not sorted_by_avg.empty else "N/A"
        
        if is_non_additive:
            with k2:
                _render_metric_card(f"Top Segment by Average {metric_name}", f"Top Segment by Average {metric_name}", top_avg_segment)
                top_avg_row = sorted_by_avg.iloc[0] if not sorted_by_avg.empty else None
                if top_avg_row is not None:
                    formatted_avg = _format_number(top_avg_row['Avg Value'])
                    st.markdown(f"""
                        <div class="metric-context-card">
                            <div class="context-row">
                                <span class="context-label">Average {metric_name}</span>
                                <span class="context-value">{formatted_avg}</span>
                            </div>
                            <div class="context-row">
                                <span class="context-label">Customers</span>
                                <span class="context-value">{top_avg_row['Records']:,}</span>
                            </div>
                            <div class="context-row">
                                <span class="context-label">Share</span>
                                <span class="context-value">{top_avg_row['Share']}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            k3.metric("Chart Mode", "Average (Auto)")
            return sorted_by_avg.head(12).copy(), "Avg Value", is_non_additive, top_total_segment, top_avg_segment, None, None, None
        else:
            with k2:
                _render_metric_card(f"Top Segment by {metric_name}", f"Top Segment by {metric_name}", top_total_segment)
            k3.metric(f"Highest Avg {metric_name}", str(top_avg_segment))
            return sorted_by_total.head(12).copy(), "Total Value", is_non_additive, top_total_segment, top_avg_segment, None, None, None
    else:
        sorted_by_records = segment_table.sort_values("Records", ascending=False)
        top_segment = sorted_by_records.iloc[0][selected_cat] if not sorted_by_records.empty else "N/A"
        top_share = sorted_by_records.iloc[0]["Share"] if not sorted_by_records.empty else "0%"
        top_count = sorted_by_records.iloc[0]["Records"] if not sorted_by_records.empty else 0
        total_count = segment_table["Records"].sum()
        percentage = (top_count / total_count * 100) if total_count > 0 else 0
        
        with k2:
            _render_metric_card("Top Segment by Customer Count", "Top Segment by Customer Count", top_segment)
        k3.metric("Largest Share", str(top_share))
        return sorted_by_records.head(12).copy(), "Records", False, None, None, top_segment, top_count, percentage

def _render_segment_insights(selected_metric, is_non_additive, segment_name, metric_name, top_total_segment, top_avg_segment, top_segment, top_count, percentage):
    c1, c2 = st.columns(2)
    with c1:
        if selected_metric:
            if is_non_additive:
                st.info(f"**Summary**\n{top_avg_segment} has the highest average {metric_name}.")
            else:
                st.info(f"**Summary**\n{top_total_segment} is the leading {segment_name} in terms of total {metric_name}.")
        else:
            st.info(f"**Summary**\n{top_segment} is the most popular {segment_name} with {top_count:,} records, covering {percentage:.1f}% of valid data.")
    with c2:
        if not selected_metric:
            if percentage >= 50:
                st.warning("**Customer insight**\nOne segment dominates the dataset. Track it separately so overall performance is not hiding weaker segments.")
            else:
                st.success("**Customer insight**\nThe segment mix is reasonably distributed, which makes comparison across groups more useful.")
        else:
            st.success(f"**Customer insight**\nComparing segments by {metric_name} reveals which groups drive the most value, rather than just transaction volume.")

# ==========================================
# 4. Chart helpers
# ==========================================

def _render_segment_chart(chart_df, selected_cat, y_col, segment_name, metric_name=None, is_non_additive=False):
    chart_title = f"{'Average' if is_non_additive else 'Total'} {metric_name} by {segment_name}" if metric_name else f"Record Count by {segment_name}"
    custom_data = ["Formatted Metric", "Records", "Share"] if metric_name else ["Records", "Share"]
    
    if metric_name:
        chart_df["Formatted Metric"] = chart_df[y_col].apply(_format_number)
        
    fig = px.bar(
        chart_df, x=selected_cat, y=y_col, text=y_col,
        title=chart_title, labels={selected_cat: segment_name, y_col: y_col},
        custom_data=custom_data
    )
    
    if metric_name:
        metric_prefix = "Average" if is_non_additive else "Total"
        hovertemplate = (
            f"<b>{segment_name}:</b><br>%{{x}}<br><br>"
            f"<b>{metric_prefix} {metric_name}:</b><br>%{{customdata[0]}}<br><br>"
            "<b>Customers:</b><br>%{customdata[1]:,}<br><br>"
            "<b>Share:</b><br>%{customdata[2]}<extra></extra>"
        )
    else:
        hovertemplate = (
            f"<b>{segment_name}:</b><br>%{{x}}<br><br>"
            "<b>Customers:</b><br>%{customdata[0]:,}<br><br>"
            "<b>Share:</b><br>%{customdata[2]}<extra></extra>"
        )
        # Note: Original code mapped %{customdata[1]} for share in the non-metric branch.
        # It had custom_data=["Records", "Share"]. Index 1 is Share. 
        # I am correcting my literal string to match the original index.
        hovertemplate = (
            "<b>" + segment_name + ":</b><br>%{x}<br><br>"
            "<b>Customers:</b><br>%{customdata[0]:,}<br><br>"
            "<b>Share:</b><br>%{customdata[1]}<extra></extra>"
        )
        
    fig.update_traces(texttemplate="%{text:.2s}", textposition="outside", hovertemplate=hovertemplate)
    fig.update_layout(height=430, margin=dict(l=20, r=20, t=40, b=35))
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. Export helpers
# ==========================================

def _render_export_action(module_name, log_message, button_key):
    if st.button(f"Add {module_name} to Export Report", key=button_key, type="primary"):
        add_session_log(log_message)
        st.success(f"{module_name} has been added to your Customer Insights Report draft. You can review, edit, and export the complete report later from the Export Center.")
    st.info(
        "This action does not download a report. It stores the current analysis so that all completed modules "
        "(Dashboard, Data Cleaning, Segment Analysis, Customer Analytics, AI Summary, etc.) can be combined "
        "into one professional report in the Export Center."
    )

# ==========================================
# 6. Main public function
# ==========================================

def _render_segments_tab(df, cat_cols, num_cols):
    if not cat_cols:
        st.info("No usable segment fields were found. Add fields such as category, brand, region, channel, status, or customer type.")
        return

    st.markdown("#### Configuration")
    try:
        cont_config = st.container(border=True)
    except TypeError:
        cont_config = st.container()
        
    with cont_config:
        control1, control2 = st.columns([2, 1])
        with control1:
            selected_cat = st.selectbox("Segment field", cat_cols, key="cat_select", format_func=_display_column_name)
        with control2:
            selected_metric_for_segment = st.selectbox(
                "Compare by value", [None] + num_cols,
                format_func=lambda col: "Record count" if col is None else _display_column_name(col),
                key="segment_metric_select"
            )
    
    with branded_spinner("Analyzing segments..."):
        segment_name = _display_column_name(selected_cat)
        metric_name = _display_column_name(selected_metric_for_segment) if selected_metric_for_segment else None
        segment_table = get_cached_metric(f"segment_table_{selected_cat}_{selected_metric_for_segment}", _build_segment_table, df, selected_cat, selected_metric_for_segment)
        segment_count = segment_table.shape[0]
        
        st.markdown(f"### {segment_name} Overview")
        
        chart_df, y_col, is_non_additive, top_total_segment, top_avg_segment, top_segment, top_count, percentage = _render_segment_overview(
            segment_table, selected_cat, selected_metric_for_segment, segment_name, metric_name, segment_count
        )
        
        _render_segment_chart(chart_df, selected_cat, y_col, segment_name, metric_name, is_non_additive)
        
        with st.expander("View Detailed Table", expanded=False):
            st.dataframe(segment_table.head(25), use_container_width=True, hide_index=True)
            
        try:
            cont_insights = st.container(border=True)
        except TypeError:
            cont_insights = st.container()
            
        with cont_insights:
            st.markdown("#### 📋 segment interpretation")
            _render_segment_insights(selected_metric_for_segment, is_non_additive, segment_name, metric_name, top_total_segment, top_avg_segment, top_segment, top_count, percentage)
        
    _render_export_action("Segment Analysis", f"Reviewed segment field: {selected_cat}", "log_cat")

def _render_value_metrics_tab(df, num_cols):
    if not num_cols:
        st.info("No usable value metrics were found. Index, ID, serial, and sequence fields are removed automatically.")
        return

    st.markdown("#### Configuration")
    try:
        cont_config = st.container(border=True)
    except TypeError:
        cont_config = st.container()
        
    with cont_config:
        selected_num = st.selectbox("Value metric", num_cols, key="num_select", format_func=_display_column_name)
    
    with branded_spinner("Analyzing value metric..."):
        col_data = pd.to_numeric(df[selected_num], errors="coerce").dropna()
        if len(col_data) == 0:
            st.warning("No valid numeric data is available for this metric.")
            return

        summary = get_cached_metric(f"metric_summary_{selected_num}", _metric_summary, col_data)
        avg_val = summary["average"]
        med_val = summary["median"]
        max_val = summary["maximum"]
        min_val = summary["minimum"]
        p90_val = summary["p90"]
        
        metric_name = _display_column_name(selected_num)
        st.markdown(f"### {metric_name}")
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Average", _format_number(avg_val))
        m2.metric("Median", _format_number(med_val))
        m3.metric("Top 10% Starts At", _format_number(p90_val))
        m4.metric("Highest", _format_number(max_val))
        m5.metric("Lowest", _format_number(min_val))
        
        chart_df = pd.DataFrame({metric_name: col_data})
        fig = px.histogram(chart_df, x=metric_name, nbins=30)
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=25, b=35))
        st.plotly_chart(fig, use_container_width=True)
        
        if med_val != 0 and avg_val > med_val + (0.1 * abs(med_val)):
            distribution_note = "A smaller set of high-value records is lifting the average above the median."
        elif med_val != 0 and avg_val < med_val - (0.1 * abs(med_val)):
            distribution_note = "Lower-value records are pulling the average below the median."
        else:
            distribution_note = "The average and median are close, so the metric is relatively stable across records."
            
        try:
            cont_insights = st.container(border=True)
        except TypeError:
            cont_insights = st.container()
            
        with cont_insights:
            st.markdown("#### 📋 metric interpretation")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**Readout**\nTypical value is {_format_number(med_val)}. The high-value threshold starts around {_format_number(p90_val)}.")
            with c2:
                st.warning(f"**Interpretation**\n{distribution_note}")
    
            st.success(f"Use {_format_number(p90_val)} and above as the review band for high-value records. Use the median as the normal operating baseline.")

    _render_export_action("Metric Analysis", f"Reviewed value metric: {selected_num}", "log_num")

def show_analysis():
    render_header(
        "Data Explorer",
        "Understand which customer groups, products, and value drivers deserve attention.",
        "Data Explorer"
    )
    
    render_help_expander(
        "Use this page to compare meaningful customer segments and value metrics. Technical fields "
        "such as row indexes, IDs, and serial numbers are excluded from analysis."
    )

    df, source_label, source_name = get_analytics_df("marketplace")
    render_data_source_banner(source_label, source_name)

    if df is None or df.empty:
        render_empty_state()
        render_footer("Data Explorer")
        return
    st.session_state["has_analysis"] = True

    st.markdown("## Segment Analysis")
    
    cat_cols, excluded_cat_cols = _split_segment_columns(df)
    num_cols, excluded_num_cols = _split_numeric_columns(df)
    
    if st.session_state.get("cat_select") not in cat_cols:
        st.session_state.pop("cat_select", None)
    if st.session_state.get("num_select") not in num_cols:
        st.session_state.pop("num_select", None)
    if st.session_state.get("segment_metric_select") not in [None] + num_cols:
        st.session_state.pop("segment_metric_select", None)
    
    if excluded_num_cols or excluded_cat_cols:
        with st.expander("Fields excluded from this analysis", expanded=False):
            if excluded_num_cols:
                cols_str = ", ".join(_display_column_name(col) for col in excluded_num_cols)
                st.write(f"Numeric fields excluded: {cols_str}")
            if excluded_cat_cols:
                cols_str = ", ".join(_display_column_name(col) for col in excluded_cat_cols)
                st.write(f"Segment fields excluded: {cols_str}")

    tab1, tab2 = st.tabs(["Segments", "Value Metrics"])
    
    with tab1:
        _render_segments_tab(df, cat_cols, num_cols)
        
    with tab2:
        _render_value_metrics_tab(df, num_cols)
        
    st.divider()
    st.info("Next step: Open Customer Analytics to review dashboards, customer groups, and retention signals.")
    render_footer("Data Explorer")
