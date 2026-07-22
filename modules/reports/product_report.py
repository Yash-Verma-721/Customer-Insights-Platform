import pandas as pd
from utils.customer_metrics import money
from modules.reports.report_utils import build_module_report

def build_product_report_blocks(product_metrics, top_products=pd.DataFrame()):
    metrics = [
        ("Total Products", f"{product_metrics.get('total_products', 0):,}"),
        ("Categories", f"{product_metrics.get('total_categories', 0):,}"),
        ("Avg Price", money(product_metrics.get("avg_price", 0)))
    ]
    
    insights = [
        f"The top performing product/category is '{product_metrics.get('best_product', 'N/A')}' generating {money(product_metrics.get('best_product_revenue', 0))}.",
        f"The lowest performing product generated {money(product_metrics.get('lowest_product_revenue', 0))}."
    ]
    
    tables = []
    if not top_products.empty:
        tables.append({
            "title": "Top Products by Revenue",
            "df": top_products.head(10),
            "placement": "after_insights"
        })
        
    return build_module_report(
        title="Product Analytics Report",
        metrics=metrics,
        insights=insights,
        tables=tables
    )
