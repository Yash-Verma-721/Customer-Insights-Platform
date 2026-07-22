import pandas as pd
from utils.customer_metrics import percent, money
from modules.reports.report_utils import build_module_report

def build_payment_report_blocks(payment_metrics, top_methods_df=pd.DataFrame()):
    metrics = [
        ("Total Revenue", money(payment_metrics.get("total_revenue", 0))),
        ("Payment Methods", f"{payment_metrics.get('total_methods', 0)}"),
        ("Success Rate", percent(payment_metrics.get("success_rate", 0))),
        ("Failed Payments", f"{payment_metrics.get('failed_count', 0):,}")
    ]
    
    if payment_metrics.get("failed_count", 0) > 100:
        insights = [
            f"There have been {payment_metrics.get('failed_count', 0):,} failed payments. This requires immediate technical investigation to prevent revenue leakage.",
            f"The overall payment success rate is {percent(payment_metrics.get('success_rate', 0))}."
        ]
    else:
        insights = [
            f"Payment failures are within normal operating limits ({payment_metrics.get('failed_count', 0):,} failed).",
            f"The overall payment success rate is {percent(payment_metrics.get('success_rate', 0))}."
        ]
    
    tables = []
    if not top_methods_df.empty:
        tables.append({
            "title": "Methods by Volume",
            "df": top_methods_df,
            "placement": "after_insights"
        })
        
    return build_module_report(
        title="Payment Analytics Report",
        metrics=metrics,
        insights=insights,
        tables=tables
    )
