import pandas as pd
from utils.customer_metrics import money, percent
from modules.reports.report_utils import build_module_report

def build_vendor_report_blocks(vendor_metrics, top_vendors=pd.DataFrame()):
    metrics = []
    
    if "total_vendors" in vendor_metrics:
        metrics.append(("Total Companies", f"{vendor_metrics.get('total_vendors', 0):,}"))
    if "total_revenue" in vendor_metrics:
        metrics.append(("Total Revenue", money(vendor_metrics.get("total_revenue", 0))))
    if "total_orders" in vendor_metrics:
        metrics.append(("Total Orders", f"{vendor_metrics.get('total_orders', 0):,}"))
    if "avg_order_value" in vendor_metrics:
        metrics.append(("Avg Order Value", money(vendor_metrics.get("avg_order_value", 0))))
    if "avg_rating" in vendor_metrics:
        metrics.append(("Avg Rating", f"{vendor_metrics.get('avg_rating', 0):.1f}/5.0" if vendor_metrics.get("avg_rating") else "N/A"))
        
    insights = []
    if "top_vendor_by_revenue" in vendor_metrics:
        insights.append(f"The top performing company by revenue is '{vendor_metrics.get('top_vendor_by_revenue', 'N/A')}' generating {money(vendor_metrics.get('top_vendor_revenue', 0))}.")
    if "lowest_vendor_revenue" in vendor_metrics:
        insights.append(f"The lowest performing company generated {money(vendor_metrics.get('lowest_vendor_revenue', 0))}.")
        
    tables = []
    if not top_vendors.empty:
        tables.append({
            "title": "Top Companies by Revenue",
            "df": top_vendors,
            "placement": "after_insights"
        })
        
    return build_module_report(
        title="Company Analytics Report",
        metrics=metrics,
        insights=insights,
        tables=tables
    )
