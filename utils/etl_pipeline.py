import time

import pandas as pd

from utils.customer_metrics import detect_customer_columns, detect_marketplace_columns
from utils.ui_helpers import calculate_readiness_score

MISSING_TOKENS = {"", "na", "n/a", "null", "none"}
IDENTIFIER_KEYWORDS = {
    "id",
    "ids",
    "code",
    "number",
    "no",
    "sku",
    "zip",
    "postal",
    "phone",
    "mobile",
    "contact",
    "invoice",
    "order",
    "product",
    "vendor",
    "customer",
    "transaction",
    "txn",
    "receipt",
}
DATE_KEYWORDS = {"date", "time", "timestamp", "created", "updated"}


def load_dataset(uploaded_file):
    """Load a CSV or Excel upload into a dataframe."""
    file_name = getattr(uploaded_file, "name", "").lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if file_name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)

    raise ValueError("Unsupported file format. Please upload a CSV or XLSX file.")


def validate_dataset(df):
    """Validate that the loaded dataframe can enter the customer analytics workflow."""
    errors = []
    warnings = []

    if df is None:
        errors.append("No dataset was loaded.")
        row_count = 0
        column_count = 0
    else:
        row_count = len(df)
        column_count = len(df.columns)

        if df.empty:
            errors.append("The uploaded dataset is empty.")
        if column_count == 0:
            errors.append("The uploaded dataset does not contain any columns.")

        duplicate_columns = df.columns[df.columns.duplicated()].tolist()
        if duplicate_columns:
            warnings.append(
                "Duplicate column names detected: " + ", ".join(map(str, duplicate_columns[:5]))
            )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_rows": row_count,
        "total_columns": column_count,
    }


def _is_identifier_column(column_name):
    normalized = str(column_name).strip().lower().replace("_", " ").replace("-", " ")
    parts = set(normalized.split())
    if parts.intersection(IDENTIFIER_KEYWORDS):
        return True
    return normalized.endswith(" id") or normalized.endswith(" code") or normalized.endswith(" no")


def _is_date_candidate_column(column_name):
    normalized = str(column_name).strip().lower().replace("_", " ").replace("-", " ")
    parts = set(normalized.split())
    return bool(parts.intersection(DATE_KEYWORDS))


def _standardize_text_series(series):
    text = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    missing_mask = text.str.lower().isin(MISSING_TOKENS)
    return text.mask(missing_mask, pd.NA)


def _infer_numeric_series(series):
    converted = pd.to_numeric(series, errors="coerce")
    non_missing = series.notna().sum()
    if non_missing == 0:
        return series

    valid_ratio = converted.notna().sum() / non_missing
    if valid_ratio >= 0.95:
        return converted
    return series


def _infer_datetime_series(series):
    converted = pd.to_datetime(series, errors="coerce")
    non_missing = series.notna().sum()
    if non_missing == 0:
        return series

    valid_ratio = converted.notna().sum() / non_missing
    if valid_ratio >= 0.95:
        return converted
    return series


def transform_dataset(df):
    """Standardize dataset values without deleting rows or creating features."""
    transformed = df.copy()
    summary = {
        "trimmed_text_columns": [],
        "standardized_missing_values": 0,
        "numeric_columns_inferred": [],
        "date_columns_inferred": [],
        "identifier_columns_skipped": [],
    }

    for column in transformed.columns:
        if pd.api.types.is_object_dtype(transformed[column]) or pd.api.types.is_string_dtype(transformed[column]):
            before_missing = transformed[column].isna().sum()
            text_series = _standardize_text_series(transformed[column])
            after_missing = text_series.isna().sum()
            transformed[column] = text_series
            summary["trimmed_text_columns"].append(column)
            summary["standardized_missing_values"] += int(after_missing - before_missing)

            if _is_identifier_column(column):
                summary["identifier_columns_skipped"].append(column)
                continue

            numeric_series = _infer_numeric_series(transformed[column])
            if pd.api.types.is_numeric_dtype(numeric_series):
                transformed[column] = numeric_series
                summary["numeric_columns_inferred"].append(column)
                continue

            if _is_date_candidate_column(column):
                datetime_series = _infer_datetime_series(transformed[column])
                if pd.api.types.is_datetime64_any_dtype(datetime_series):
                    transformed[column] = datetime_series
                    summary["date_columns_inferred"].append(column)

    return transformed, summary


def _safe_feature_name(source_column, suffix, existing_columns, feature_columns):
    feature_name = f"{source_column}_{suffix}"
    if feature_name in existing_columns or feature_name in feature_columns:
        return None
    return feature_name


def _age_group(series):
    numeric_age = pd.to_numeric(series, errors="coerce")
    return pd.cut(
        numeric_age,
        bins=[0, 17, 25, 35, 45, 60, float("inf")],
        labels=["Under 18", "18-25", "26-35", "36-45", "46-60", "60+"],
        right=True,
    )


def _value_bucket(series):
    numeric_value = pd.to_numeric(series, errors="coerce")
    valid_values = numeric_value.dropna()
    if valid_values.nunique() < 3:
        return None

    try:
        ranked_values = numeric_value.rank(method="first")
        return pd.qcut(
            ranked_values,
            q=3,
            labels=["Low", "Medium", "High"],
        )
    except ValueError:
        return None


def engineer_features(df):
    """Create safe derived features separately without modifying the source dataframe."""
    engineered_features = pd.DataFrame(index=df.index)
    feature_summary = {
        "date_features_created": [],
        "age_features_created": [],
        "revenue_features_created": [],
        "skipped_features": [],
    }
    existing_columns = set(df.columns)

    detected = detect_customer_columns(df)
    date_columns = list(dict.fromkeys(
        list(df.select_dtypes(include=["datetime"]).columns) + detected.get("date", [])
    ))

    for column in date_columns:
        if column not in df.columns:
            continue

        if pd.api.types.is_datetime64_any_dtype(df[column]):
            date_series = df[column]
        else:
            date_series = _infer_datetime_series(df[column])
            if not pd.api.types.is_datetime64_any_dtype(date_series):
                feature_summary["skipped_features"].append(f"{column}: date conversion skipped")
                continue

        date_parts = {
            "year": date_series.dt.year,
            "month": date_series.dt.month,
            "day": date_series.dt.day,
            "quarter": date_series.dt.quarter,
            "weekday": date_series.dt.day_name(),
            "is_weekend": date_series.dt.dayofweek >= 5,
        }
        for suffix, values in date_parts.items():
            feature_name = _safe_feature_name(
                column, suffix, existing_columns, set(engineered_features.columns)
            )
            if feature_name:
                engineered_features[feature_name] = values
                feature_summary["date_features_created"].append(feature_name)

    age_columns = [
        column for column in df.columns
        if str(column).strip().lower().replace("_", " ").replace("-", " ") in {"age", "customer age"}
    ]
    for column in age_columns:
        feature_name = _safe_feature_name(
            column, "group", existing_columns, set(engineered_features.columns)
        )
        if feature_name:
            engineered_features[feature_name] = _age_group(df[column])
            feature_summary["age_features_created"].append(feature_name)

    revenue_columns = detected.get("revenue", [])
    for column in revenue_columns[:1]:
        if column not in df.columns:
            continue
        feature_name = _safe_feature_name(
            column, "bucket", existing_columns, set(engineered_features.columns)
        )
        if feature_name:
            bucket_series = _value_bucket(df[column])
            if bucket_series is None:
                feature_summary["skipped_features"].append(f"{column}: bucket skipped")
            else:
                engineered_features[feature_name] = bucket_series
                feature_summary["revenue_features_created"].append(feature_name)

    return engineered_features, feature_summary


def profile_dataset(df):
    """Profile dataset quality and structure using existing project scoring logic."""
    total_rows = len(df)
    total_columns = len(df.columns)

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "missing_values": int(df.isnull().sum().sum()),
        "rows_with_missing_data": int(df.isnull().any(axis=1).sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": len(df.select_dtypes(include="number").columns),
        "categorical_columns": len(df.select_dtypes(include=["object", "category", "string"]).columns),
        "date_columns": len(df.select_dtypes(include=["datetime"]).columns),
        "memory_usage_mb": float(df.memory_usage(deep=False).sum() / (1024 * 1024)),
        "readiness_score": calculate_readiness_score(df),
    }


def build_pipeline_metrics(validation, profile, processing_time):
    """Build reusable ETL monitoring metrics from validation and profiling output."""
    profile = profile or {}
    rows_loaded = int(validation.get("total_rows", 0))

    return {
        "rows_loaded": rows_loaded,
        "rows_valid": rows_loaded if validation.get("is_valid") else 0,
        "missing_cells": int(profile.get("missing_values", 0)),
        "duplicate_rows": int(profile.get("duplicate_rows", 0)),
        "numeric_columns": int(profile.get("numeric_columns", 0)),
        "categorical_columns": int(profile.get("categorical_columns", 0)),
        "datetime_columns": int(profile.get("date_columns", 0)),
        "readiness_score": int(profile.get("readiness_score", 0)),
        "processing_time": float(processing_time),
    }


def prepare_dataset(uploaded_file):
    """Run the first ETL pass: load, validate, transform, profile, and detect useful columns."""
    start_time = time.perf_counter()
    df = load_dataset(uploaded_file)
    validation = validate_dataset(df)

    if not validation["is_valid"]:
        processing_time = time.perf_counter() - start_time
        return {
            "dataframe": df,
            "validation": validation,
            "transform": None,
            "engineered_features": pd.DataFrame(),
            "feature_summary": {
                "date_features_created": [],
                "age_features_created": [],
                "revenue_features_created": [],
                "skipped_features": [],
            },
            "profile": None,
            "pipeline_metrics": build_pipeline_metrics(validation, None, processing_time),
            "detected_columns": {
                "customer": {},
                "marketplace": {},
            },
        }

    transformed_df, transform_summary = transform_dataset(df)
    engineered_features, feature_summary = engineer_features(transformed_df)
    profile = profile_dataset(transformed_df)
    processing_time = time.perf_counter() - start_time

    return {
        "dataframe": transformed_df,
        "validation": validation,
        "transform": transform_summary,
        "engineered_features": engineered_features,
        "feature_summary": feature_summary,
        "profile": profile,
        "pipeline_metrics": build_pipeline_metrics(validation, profile, processing_time),
        "detected_columns": {
            "customer": detect_customer_columns(transformed_df),
            "marketplace": detect_marketplace_columns(transformed_df),
        },
    }
