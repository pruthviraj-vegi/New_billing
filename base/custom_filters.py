from django import template
import locale
import base64
from datetime import datetime, timedelta
from django.conf import settings

locale.setlocale(locale.LC_ALL, "en_IN")

register = template.Library()

formate = {
    "grouping": True,  # Enable thousands grouping
    "grouping_threshold": 3,  # Group digits in threes
    "decimal_point": ".",  # Use dot as the decimal separator
    "frac_digits": 2,  # Show 2 digits after the decimal point
}


@register.filter(name="currency")
def currency(value, arg=None):
    try:
        if value is None:
            return "0.00"

        return locale.format_string(
            "%%.%df" % formate["frac_digits"],
            value,
            grouping=formate["grouping"],
            monetary=False,
        )
    except (TypeError, ValueError) as e:
        print(e)
        return value


@register.filter(name="currency_nonDecimal")
def currency_nonDecimal(value, arg=None):
    try:
        if value is None:
            return "0"

        value_int = int(value)

        return locale.format_string(
            "%d",
            value_int,
            grouping=formate["grouping"],
            monetary=False,
        )
    except (TypeError, ValueError) as e:
        return value


@register.filter(name="currency_abbreviation")
def currency_abbreviation(value):
    """
    Formats a number into an international currency format or a 'k' abbreviation.

    Examples:
    1000 -> 1k
    100000 -> 100,000.00 (or localized equivalent)
    1234567 -> 1.23M
    """
    try:
        if value is None:
            return "0.00"

        # Check for 'k', 'M', 'B' abbreviations
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        elif value >= 1000:
            return f"{value / 1000:.1f}k"

        # Set locale for international formatting (e.g., thousands separators)
        # You may need to set this globally in your Django settings or project entry point
        # For example: locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        # Here, we'll try a default to ensure it works
        try:
            locale.setlocale(locale.LC_ALL, "")
        except locale.Error:
            # Fallback if the system's default locale isn't set
            locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

        # Use locale.format_string for international formatting
        # locale.format_string requires a format specifier like "%.2f"
        return locale.format_string("%.2f", value, grouping=True)

    except (TypeError, ValueError):
        return value


@register.filter(name="phone_number")
def phone_number(value):
    return f"+91 {value}"

@register.filter(name="b64encode")
def base64_encode(value):
    return base64.b64encode(value).decode("utf-8")


@register.filter(name="sub")
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value) - float(arg)
    except (TypeError, ValueError):
        return value


@register.filter(name="div")
def div(value, arg):
    """Divide the value by the arg."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter(name="status_badge")
def status_badge(value):
    if str(value).lower() in ["active", "success", "true", "accepted"]:
        return "badge bg-success"
    elif str(value).lower() in ["inactive", "error", "danger", "false", "rejected"]:
        return "badge bg-danger"
    elif str(value).lower() in ["pending", "warning"]:
        return "badge bg-warning"
    else:
        return "badge bg-secondary"


@register.filter(name="add_class")
def add_class(field, css_class):
    """
    Add a CSS class to a form field
    Usage: {{ form.field|add_class:"form-control" }}
    """
    return field.as_widget(attrs={"class": css_class})


@register.filter(name="to_datetime")
def to_datetime(value):
    """Parse ISO 8601 string to datetime, or pass through datetime.

    Returns None if parsing fails.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        # Normalize Zulu suffix to fromisoformat compatible form
        if text.endswith("Z"):
            text = text[:-1]
        try:
            return datetime.fromisoformat(text)
        except Exception:
            return None
    return None


@register.filter(name="expiry")
def expiry(value):
    """Compute expiry datetime by adding INACTIVITY_TIMEOUT_SECONDS to value.

    Accepts datetime or ISO string. Returns datetime or None.
    """
    dt = value if isinstance(value, datetime) else to_datetime(value)
    if dt is None:
        return None
    timeout_seconds = getattr(settings, "INACTIVITY_TIMEOUT_SECONDS", 3 * 60 * 60)
    return dt + timedelta(seconds=timeout_seconds)
