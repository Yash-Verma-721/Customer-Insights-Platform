import pandas as pd
from utils.customer_metrics import money
from modules.reports.report_utils import build_module_report

def build_vendor_report_blocks(vendor_metrics, top_vendors=pd.DataFrame()):
    metrics = [
        ("Total Vendors", f"{vendor_metrics.get('total_vendors', 0):,}"),
        ("Total Revenue", money(vendor_metrics.get("total_revenue", 0))),
        ("Total Orders", f"{vendor_metrics.get('total_orders', 0):,}"),
        ("Avg Order Value", money(vendor_metrics.get("avg_order_value", 0))),
        ("Avg Rating", f"{vendor_metrics.get('avg_rating', 0):.1f}/5.0" if vendor_metrics.get("avg_rating") else "N/A")
    ]
    
    insights = [
        f"The top performing vendor by revenue is '{vendor_metrics.get('top_vendor_by_revenue', 'N/A')}' generating {money(vendor_metrics.get('top_vendor_revenue', 0))}.",
        f"The lowest performing vendor generated {money(vendor_metrics.get('lowest_vendor_revenue', 0))}."
    ]
    
    tables = []
    if not top_vendors.empty:
        tables.append({
            "title": "Top 10 Vendors by Revenue",
            "df": top_vendors.head(10),
            "placement": "after_insights"
        })
        
    return build_module_report(
        title="Vendor Analytics Report",
        metrics=metrics,
        insights=insights,
        tables=tables
    )
