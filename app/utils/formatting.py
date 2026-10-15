"""
Utility functions for formatting and display.
"""
import time
from datetime import datetime


def format_bytes(nbytes: int | float, precision: int = 1) -> str:
    """Format bytes into human-readable string."""
    if nbytes < 0:
        return "N/A"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    idx = 0
    value = float(nbytes)
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.{precision}f} {units[idx]}"


def format_speed(bytes_per_sec: float, precision: int = 1) -> str:
    """Format bytes/sec into readable speed."""
    if bytes_per_sec < 0:
        return "N/A"
    return f"{format_bytes(bytes_per_sec, precision)}/s"


def format_uptime(seconds: float) -> str:
    """Format uptime in seconds to human-readable string."""
    if seconds < 0:
        return "N/A"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def format_timestamp(ts: float) -> str:
    """Format unix timestamp to readable string."""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "N/A"


def severity_color(severity: str) -> str:
    """Return hex color for severity level."""
    colors = {
        'Healthy': '#82B9B1',      # Muted teal
        'Information': '#A4A69F',  # Neutral gray
        'Warning': '#E5A93C',      # Restrained amber
        'Critical': '#E05252',     # Clear red
    }
    return colors.get(severity, '#A4A69F')


def health_score_color(score: float) -> str:
    """Return hex color for health score."""
    if score >= 80:
        return '#82B9B1'  # Muted teal (healthy)
    elif score >= 60:
        return '#E8FF65'  # Acid lime (good/fair)
    elif score >= 40:
        return '#E5A93C'  # Amber (warning/degraded)
    else:
        return '#E05252'  # Clear red (critical)


def health_score_label(score: float) -> str:
    """Return label for health score."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Fair"
    elif score >= 40:
        return "Degraded"
    elif score >= 20:
        return "Poor"
    else:
        return "Critical"
