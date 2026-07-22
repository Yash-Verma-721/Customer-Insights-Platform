import pandas as pd
from utils.customer_metrics import percent
from modules.reports.report_utils import build_module_report

def build_customer_report_blocks(cust_metrics, ml_metrics, ml_summ):
    metrics = [
        ("Total Customers", f"{cust_metrics.get('total_customers', 0):,}"),
        ("Repeat Purchase Rate", percent(cust_metrics.get("repeat_rate", 0))),
        ("Purchase Frequency", f"{cust_metrics.get('purchase_frequency', 1.0):.2f}x"),
        ("One-Time Customers", f"{cust_metrics.get('one_time_customers', 0):,}")
    ]
    
    tables = []
    if ml_metrics and ml_metrics.get("status") == "success" and ml_summ is not None and not ml_summ.empty:
        tables.append({
            "title": "Customer Segments",
            "df": ml_summ[["ml_segment", "customer_count", "percentage"]],
            "placement": "before_insights"
        })
    else:
        tables.append({
            "empty_message": "ML Segmentation data is not available.",
            "placement": "before_insights"
        })
        
    insights = [
        f"The top 10% of customers drive {percent(cust_metrics.get('top_10_revenue_share', 0))} of total revenue.",
        f"A total of {cust_metrics.get('one_time_customers', 0):,} customers have only purchased once, indicating a churn risk or acquisition focus."
    ]
    
    return build_module_report(
        title="Customer Analytics Report",
        metrics=metrics,
        tables=tables,
        insights=insights
    )
