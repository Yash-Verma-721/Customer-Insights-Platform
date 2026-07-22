import pandas as pd
from utils.customer_metrics import money, percent
from modules.reports.report_utils import build_module_report

def build_sales_report_blocks(sales_metrics, forecast=None):
    metrics = [
        ("Total Sales", money(sales_metrics.get("total_sales", 0))),
        ("Avg Order Value", money(sales_metrics.get("avg_order_value", 0))),
        ("Avg Daily Sales", money(sales_metrics.get("avg_daily_sales", 0))),
        ("Growth %", percent(sales_metrics.get("growth_pct", 0)))
    ]
    
    insights = [
        f"The highest revenue generated was in {sales_metrics.get('best_month', 'N/A')}.",
        f"The lowest revenue generated was in {sales_metrics.get('worst_month', 'N/A')}."
    ]
    
    if forecast:
        forecast["formatted_target"] = money(forecast.get("forecast_revenue", 0))
        
    return build_module_report(
        title="Sales Analytics Report",
        metrics=metrics,
        insights=insights,
        forecast=forecast
    )
