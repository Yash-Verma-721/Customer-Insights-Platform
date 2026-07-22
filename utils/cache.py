import streamlit as st

def increment_dataset_version():
    """Increments the dataset version and clears the old analytics cache to prevent memory bloat."""
    if "dataset_version" not in st.session_state:
        st.session_state.dataset_version = 1
    else:
        st.session_state.dataset_version += 1
        
    if "analytics_cache" in st.session_state:
        st.session_state.analytics_cache.clear()

def get_cached_metric(cache_key, compute_func, *args, **kwargs):
    """
    Retrieves or computes a metric using the dataset_version as part of the cache namespace.
    Guarantees that stale analytical objects are never reused accidentally.
    """
    if "dataset_version" not in st.session_state:
        st.session_state.dataset_version = 1
        
    if "analytics_cache" not in st.session_state:
        st.session_state.analytics_cache = {}
        
    version = st.session_state.dataset_version
    namespaced_key = f"v{version}_{cache_key}"
    
    if namespaced_key not in st.session_state.analytics_cache:
        result = compute_func(*args, **kwargs)
        st.session_state.analytics_cache[namespaced_key] = result
        
        if getattr(compute_func, '__name__', '') == 'build_customer_profile':
            try:
                from utils.ml_models import run_ml_segmentation_pipeline
                if isinstance(result, tuple) and len(result) >= 1:
                    run_ml_segmentation_pipeline(result[0])
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"ML Pipeline hook skipped: {e}")
                
    return st.session_state.analytics_cache[namespaced_key]
