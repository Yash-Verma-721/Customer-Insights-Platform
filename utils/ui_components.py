import streamlit as st
from contextlib import contextmanager
from utils.ui_constants import (
    COLORS, STATUS_COLORS, STATUS_BG_COLORS, ICONS, SPACING,
    ICON_TREND_UP, ICON_TREND_DOWN, ICON_TREND_FLAT,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO, COLOR_NEUTRAL
)

def _clean_st_icon(icon: str):
    """
    Sanitize icon string for native Streamlit widget parameters (e.g. st.info, st.subheader).
    Streamlit expects single character emojis, shortcodes like ':material/name:', or None.
    """
    if not icon:
        return None
    if len(icon) == 1:
        return icon
    if icon.startswith(":") and icon.endswith(":"):
        return icon
    if isinstance(icon, str) and (icon.isalnum() or "_" in icon):
        return f":material/{icon}:"
    return None

def _safe_st_alert(alert_type: str, msg: str, icon: str = None):
    """
    Safely invoke native Streamlit alert widget with fallbacks if icon formatting fails.
    """
    st_func = st.info
    if alert_type == "success":
        st_func = st.success
    elif alert_type == "warning":
        st_func = st.warning
    elif alert_type in ("danger", "error"):
        st_func = st.error

    clean_icon = _clean_st_icon(icon)
    try:
        if clean_icon:
            st_func(msg, icon=clean_icon)
            return
    except Exception:
        pass
    
    st_func(msg)

@contextmanager
def page_wrapper():
    """
    Context manager to enforce a consistent page layout width and padding.
    Global font styles and icons are loaded in assets/style.css.
    """
    st.markdown("<div class='sys-page-wrapper'>", unsafe_allow_html=True)
    yield
    st.markdown("</div>", unsafe_allow_html=True)

def page_header(
    title: str,
    subtitle: str = None,
    icon: str = None,
    help: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    extra_css_class: str = None,
    status_text: str = None,
    status_type: str = "success"
):
    """
    Render a standard page header using native Streamlit widgets.
    """
    clean_icon = _clean_st_icon(icon)
    header_text = f"{clean_icon} {title}" if clean_icon else title
        
    try:
        st.title(header_text, help=help or tooltip)
    except Exception:
        st.title(title, help=help or tooltip)

    if subtitle:
        st.caption(subtitle)
    if status or status_text:
        badge_text = status or status_text
        st.markdown(f"<span class='sys-badge {status_type}'>{badge_text}</span>", unsafe_allow_html=True)

def render_page_header(title, subtitle=None, status_text=None, status_type="success"):
    """
    Backwards-compatible wrapper for page header.
    """
    page_header(title=title, subtitle=subtitle, status_text=status_text, status_type=status_type)

def section_header(
    title: str,
    subtitle: str = None,
    divider: bool = True,
    icon: str = None,
    help: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    action_text: str = None,
    action_icon: str = None,
    extra_css_class: str = None
):
    """
    Render a section header with optional subtitle, divider, and actions using native Streamlit components.
    """
    clean_action_icon = _clean_st_icon(action_icon)
    if action_text:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(title, help=help or tooltip)
            if subtitle:
                st.caption(subtitle)
        with col2:
            try:
                st.button(action_text, icon=clean_action_icon, key=f"sec_act_{title}")
            except Exception:
                st.button(action_text, key=f"sec_act_{title}")
    else:
        st.subheader(title, help=help or tooltip)
        if subtitle:
            st.caption(subtitle)
            
    if divider:
        st.divider()

def render_section_header(title, action_text=None, action_icon=None):
    """
    Backwards-compatible wrapper for section header.
    """
    section_header(title=title, action_text=action_text, action_icon=action_icon, divider=False)

def kpi_card(
    label: str,
    value: str,
    delta: str = None,
    delta_color: str = "normal",
    help: str = None,
    icon: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    extra_css_class: str = None,
    trend_value: str = None,
    trend_direction: str = None
):
    """
    Render a KPI Card using native Streamlit metric widget.
    """
    display_delta = delta or trend_value
    if trend_direction and delta_color == "normal":
        delta_color = "normal" if trend_direction == "up" else "inverse" if trend_direction == "down" else "off"
        
    st.metric(
        label=label,
        value=value,
        delta=display_delta,
        delta_color=delta_color,
        help=help or tooltip
    )

def render_kpi_card(title, value, trend_value=None, trend_direction=None, icon=None):
    """
    Backwards-compatible wrapper for KPI card delegating to native kpi_card implementation.
    """
    kpi_card(
        label=title,
        value=value,
        trend_value=trend_value,
        trend_direction=trend_direction,
        icon=icon
    )

def info_card(
    title: str,
    body: str,
    icon: str = None,
    alert_type: str = "info",
    help: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    extra_css_class: str = None
):
    """
    Render an information card using native Streamlit feedback alerts.
    """
    msg = f"**{title}**\n\n{body}"
    _safe_st_alert(alert_type, msg, icon=icon)

def render_info_card(title, body, icon=None, alert_type="info"):
    """
    Backwards-compatible wrapper for info card delegating to native info_card implementation.
    """
    info_card(
        title=title,
        body=body,
        icon=icon,
        alert_type=alert_type
    )

def status_badge(
    text: str,
    status_type: str = "neutral",
    icon: str = None,
    help: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    extra_css_class: str = None
):
    """
    Render a small inline status badge.
    """
    icon_span = f"<span class='material-symbols-outlined' style='font-size: 12px; margin-right: 4px;'>{icon}</span>" if icon else ""
    st.markdown(f"<span class='sys-badge {status_type}' title='{tooltip or ''}'>{icon_span}{text}</span>", unsafe_allow_html=True)

def render_status_badge(text, status_type="neutral"):
    """
    Backwards-compatible wrapper for status badge.
    """
    status_badge(text=text, status_type=status_type)

def ranking_card(
    title: str,
    items: list,
    icon: str = None,
    help: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    extra_css_class: str = None
):
    """
    Render a ranking list using native Streamlit containers and formatting.
    items: list of dicts with 'name' and 'value'
    """
    with st.container():
        if title:
            st.markdown(f"**{title}**")
        for idx, item in enumerate(items):
            rank = f"#{idx + 1}"
            name = item.get('name', 'N/A')
            val = str(item.get('value', ''))
            badge = " (★ Top)" if idx == 0 else ""
            st.markdown(f"**{rank}** {name}{badge} — `{val}`")

def render_ranking_list(items):
    """
    Backwards-compatible wrapper for ranking list delegating to native ranking_card implementation.
    """
    ranking_card(title=None, items=items)

@contextmanager
def chart_container(
    title: str = None,
    subtitle: str = None,
    icon: str = None,
    help: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    extra_css_class: str = None
):
    """
    Native Streamlit context manager for charts/visualizations.
    """
    with st.container():
        if title:
            st.markdown(f"#### {title}")
        if subtitle:
            st.caption(subtitle)
        yield

@contextmanager
def filter_toolbar(
    title: str = "Filters",
    icon: str = None,
    help: str = None,
    status: str = None,
    tooltip: str = None,
    width: str = None,
    extra_css_class: str = None
):
    """
    Native Streamlit context manager for toolbar/filtering controls.
    """
    with st.container():
        st.markdown(f"**{title}**")
        yield

def render_metric_tile(label, value, progress_pct=None):
    """
    Render a metric tile using native Streamlit widgets.
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(label)
    with col2:
        st.markdown(f"**{value}**")
    if progress_pct is not None:
        try:
            pct = min(max(float(progress_pct) / 100.0, 0.0), 1.0)
            st.progress(pct)
        except (ValueError, TypeError):
            pass

def render_table_toolbar(title, action_text=None, action_icon=None):
    """
    Render a table toolbar using native Streamlit subheader.
    """
    st.markdown(f"**{title}**")

@contextmanager
def bento_card(title=None, icon=None):
    """
    Context manager for Bento Grid card using native Streamlit container.
    """
    with st.container():
        if title:
            clean_icon = _clean_st_icon(icon)
            if clean_icon:
                try:
                    st.subheader(f"{clean_icon} {title}")
                except Exception:
                    st.subheader(title)
            else:
                st.subheader(title)
        yield
