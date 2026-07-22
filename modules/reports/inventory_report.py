import pandas as pd
from utils.customer_metrics import money
from modules.reports.report_utils import build_module_report

def build_inventory_report_blocks(inventory_metrics, stock_df=pd.DataFrame()):
    metrics = [
        ("Total Stock", f"{inventory_metrics.get('total_stock', 0):,}"),
        ("Inventory Value", money(inventory_metrics.get("inventory_value", 0))),
        ("Low Stock Items", f"{inventory_metrics.get('low_stock_count', 0):,}"),
        ("Out of Stock", f"{inventory_metrics.get('out_of_stock_count', 0):,}")
    ]
    
    insights = [
        f"A total of {inventory_metrics.get('low_stock_count', 0):,} products are running low on stock and need reordering.",
        f"There are {inventory_metrics.get('out_of_stock_count', 0):,} products currently out of stock."
    ]
    
    tables = []
    if not stock_df.empty:
        tables.append({
            "title": "Items Requiring Attention",
            "df": stock_df.head(10),
            "placement": "after_insights"
        })
        
    return build_module_report(
        title="Inventory Analytics Report",
        metrics=metrics,
        insights=insights,
        tables=tables
    )
