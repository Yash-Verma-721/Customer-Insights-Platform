# Centralized Enterprise Design System Constants for Stratosphere BI

# -----------------------------------------------------------------------------
# Color Tokens
# -----------------------------------------------------------------------------
COLOR_PRIMARY = "#a8c8ff"
COLOR_PRIMARY_CONTAINER = "#005fb8"
COLOR_ON_PRIMARY_CONTAINER = "#cadcff"

COLOR_SECONDARY = "#b7c8e1"
COLOR_SECONDARY_CONTAINER = "#3a4a5f"
COLOR_ON_SECONDARY_CONTAINER = "#a9bad3"

COLOR_BACKGROUND = "#111319"
COLOR_ON_BACKGROUND = "#e1e2ea"

COLOR_SURFACE = "#111319"
COLOR_ON_SURFACE = "#e1e2ea"
COLOR_SURFACE_CONTAINER = "#1d2025"
COLOR_SURFACE_CONTAINER_HIGH = "#272a30"
COLOR_SURFACE_CONTAINER_HIGHEST = "#32353b"
COLOR_SURFACE_VARIANT = "#32353b"
COLOR_ON_SURFACE_VARIANT = "#c2c6d4"

COLOR_OUTLINE = "#8c919d"
COLOR_OUTLINE_VARIANT = "#424752"

# -----------------------------------------------------------------------------
# Status & Semantic Colors
# -----------------------------------------------------------------------------
COLOR_SUCCESS = "#10b981"
COLOR_SUCCESS_BG = "rgba(16, 185, 129, 0.1)"

COLOR_WARNING = "#f59e0b"
COLOR_WARNING_BG = "rgba(245, 158, 11, 0.1)"

COLOR_DANGER = "#ef4444"
COLOR_DANGER_BG = "rgba(239, 68, 68, 0.1)"

COLOR_INFO = "#3b82f6"
COLOR_INFO_BG = "rgba(59, 130, 246, 0.1)"

COLOR_NEUTRAL = "#94a3b8"
COLOR_NEUTRAL_BG = "rgba(148, 163, 184, 0.1)"

STATUS_COLORS = {
    "success": COLOR_SUCCESS,
    "warning": COLOR_WARNING,
    "danger": COLOR_DANGER,
    "error": COLOR_DANGER,
    "info": COLOR_INFO,
    "neutral": COLOR_NEUTRAL,
}

STATUS_BG_COLORS = {
    "success": COLOR_SUCCESS_BG,
    "warning": COLOR_WARNING_BG,
    "danger": COLOR_DANGER_BG,
    "error": COLOR_DANGER_BG,
    "info": COLOR_INFO_BG,
    "neutral": COLOR_NEUTRAL_BG,
}

COLORS = {
    "primary": COLOR_PRIMARY,
    "primary_container": COLOR_PRIMARY_CONTAINER,
    "secondary": COLOR_SECONDARY,
    "secondary_container": COLOR_SECONDARY_CONTAINER,
    "background": COLOR_BACKGROUND,
    "surface": COLOR_SURFACE,
    "surface_container": COLOR_SURFACE_CONTAINER,
    "surface_container_high": COLOR_SURFACE_CONTAINER_HIGH,
    "on_surface": COLOR_ON_SURFACE,
    "on_surface_variant": COLOR_ON_SURFACE_VARIANT,
    "outline": COLOR_OUTLINE,
    "success": COLOR_SUCCESS,
    "warning": COLOR_WARNING,
    "danger": COLOR_DANGER,
    "info": COLOR_INFO,
    "neutral": COLOR_NEUTRAL,
}

# -----------------------------------------------------------------------------
# Reusable Spacing Tokens
# -----------------------------------------------------------------------------
SPACING_XS = "4px"
SPACING_SM = "8px"
SPACING_MD = "16px"
SPACING_LG = "24px"
SPACING_XL = "32px"

SPACING = {
    "xs": SPACING_XS,
    "sm": SPACING_SM,
    "md": SPACING_MD,
    "lg": SPACING_LG,
    "xl": SPACING_XL,
}

# -----------------------------------------------------------------------------
# Standard Icon Mapping
# -----------------------------------------------------------------------------
# Standard Modules
ICON_SALES = "payments"
ICON_CUSTOMER = "group"
ICON_VENDOR = "storefront"
ICON_PRODUCT = "inventory_2"
ICON_REPORT = "analytics"
ICON_ALERT = "warning"
ICON_AI = "insights"
ICON_DASHBOARD = "dashboard"
ICON_OPERATIONS = "settings_applications"
ICON_SUPPLY_CHAIN = "local_shipping"
ICON_SECURITY = "shield"

# Actions & UI
ICON_TREND_UP = "arrow_upward"
ICON_TREND_DOWN = "arrow_downward"
ICON_TREND_FLAT = "horizontal_rule"
ICON_SEARCH = "search"
ICON_NOTIFICATIONS = "notifications"
ICON_SETTINGS = "settings"
ICON_MORE = "more_horiz"
ICON_HELP = "help"
ICON_DOCS = "description"

# Semantic Status
ICON_SUCCESS = "check_circle"
ICON_WARNING = "warning"
ICON_DANGER = "error"
ICON_INFO = "info"

ICONS = {
    "sales": ICON_SALES,
    "customer": ICON_CUSTOMER,
    "vendor": ICON_VENDOR,
    "product": ICON_PRODUCT,
    "report": ICON_REPORT,
    "alert": ICON_ALERT,
    "ai": ICON_AI,
    "dashboard": ICON_DASHBOARD,
    "operations": ICON_OPERATIONS,
    "supply_chain": ICON_SUPPLY_CHAIN,
    "security": ICON_SECURITY,
    "trend_up": ICON_TREND_UP,
    "trend_down": ICON_TREND_DOWN,
    "trend_flat": ICON_TREND_FLAT,
    "search": ICON_SEARCH,
    "notifications": ICON_NOTIFICATIONS,
    "settings": ICON_SETTINGS,
    "more": ICON_MORE,
    "help": ICON_HELP,
    "docs": ICON_DOCS,
    "success": ICON_SUCCESS,
    "warning": ICON_WARNING,
    "danger": ICON_DANGER,
    "info": ICON_INFO,
}

# -----------------------------------------------------------------------------
# Common UI Labels
# -----------------------------------------------------------------------------
LABEL_TOTAL_REVENUE = "Total Revenue"
LABEL_TOTAL_CUSTOMERS = "Total Customers"
LABEL_ACTIVE_USERS = "Active Users"
LABEL_FILTER = "Filter"
LABEL_SEARCH = "Search"
LABEL_EXPORT = "Export Data"
LABEL_REFRESH = "Refresh"
LABEL_APPLY = "Apply"
LABEL_RESET = "Reset"
LABEL_STATUS = "Status"
LABEL_ACTION = "Action"
LABEL_DATE_RANGE = "Date Range"

COMMON_LABELS = {
    "total_revenue": LABEL_TOTAL_REVENUE,
    "total_customers": LABEL_TOTAL_CUSTOMERS,
    "active_users": LABEL_ACTIVE_USERS,
    "filter": LABEL_FILTER,
    "search": LABEL_SEARCH,
    "export": LABEL_EXPORT,
    "refresh": LABEL_REFRESH,
    "apply": LABEL_APPLY,
    "reset": LABEL_RESET,
    "status": LABEL_STATUS,
    "action": LABEL_ACTION,
    "date_range": LABEL_DATE_RANGE,
}
