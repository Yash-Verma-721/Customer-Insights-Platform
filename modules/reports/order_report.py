import pandas as pd
from utils.customer_metrics import percent
from modules.reports.report_utils import build_module_report

def build_order_report_blocks(total_orders, return_rate, order_status_df=pd.DataFrame()):
    metrics = [
        ("Total Orders", f"{total_orders:,}"),
        ("Return Rate", percent(return_rate))
    ]
    
    if return_rate > 5.0:
        insights = [f"The current return rate is {percent(return_rate)}, which is above the 5% warning threshold. Investigation into product quality or fulfillment is recommended."]
    else:
        insights = [f"The current return rate is {percent(return_rate)}, indicating healthy fulfillment and product satisfaction."]
    
    tables = []
    if not order_status_df.empty:
        tables.append({
            "title": "Orders by Status",
            "df": order_status_df,
            "placement": "after_insights"
        })
        
    return build_module_report(
        title="Order Analytics Report",
        metrics=metrics,
        insights=insights,
        tables=tables
    )
