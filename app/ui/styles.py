"""
OSense Design System — Linear / Swiss Precision Dark Theme
Curated color tokens, typography hierarchy, and component styling.
"""

# Color Palette — Curated Neutral Dark with Acid Lime and Muted Teal Accents
COLORS = {
    # Backgrounds
    'bg_primary': '#111315',       # Deep charcoal main background
    'bg_sidebar': '#171918',       # Differentiated charcoal sidebar
    'bg_card': '#1B1E1D',          # Primary panel surface
    'bg_panel': '#1B1E1D',         # Primary panel surface alias
    'bg_panel_alt': '#151817',     # Sub-panel / input surface
    'bg_secondary': '#151817',     # Secondary dark surface
    'bg_card_hover': '#222624',    # Subtle hover state
    'bg_selected': '#242826',      # Selected state
    'bg_input': '#151817',         # Form inputs surface

    # Borders & Separators
    'border': '#303331',           # Subtle neutral gray border
    'border_subtle': '#262928',    # Very faint boundary
    'border_light': '#424744',     # Subtle hover/active border
    'border_focus': '#E8FF65',     # Acid lime focus indicator

    # Typography
    'text_primary': '#F4F4EF',     # Warm off-white
    'text_secondary': '#A4A69F',   # Muted gray
    'text_muted': '#686B65',       # Deep muted technical labels
    'text_inverse': '#111315',     # Dark text on lime buttons

    # Accents
    'accent_lime': '#E8FF65',      # Primary accent: Acid lime
    'accent_lime_dim': '#C4DC3B',  # Pressed/dimmed lime
    'accent_lime_subtle': 'rgba(232, 255, 101, 0.10)',
    'accent_teal': '#82B9B1',      # Secondary accent: Muted teal
    'accent_teal_dim': '#689790',  # Pressed/dimmed teal
    'accent_teal_subtle': 'rgba(130, 185, 177, 0.12)',

    # Semantic Status Colors (Restrained)
    'green': '#82B9B1',            # Nominal/Healthy status (muted teal)
    'green_dim': '#689790',
    'amber': '#E5A93C',            # Restrained warning amber
    'amber_dim': '#C48D2B',
    'amber_subtle': 'rgba(229, 169, 60, 0.12)',
    'red': '#E05252',              # Clear critical red (only for genuine criticals)
    'red_dim': '#BE3E3E',
    'red_subtle': 'rgba(224, 82, 82, 0.12)',
    'orange': '#E5A93C',

    # Aliases for backwards compatibility
    'accent_violet': '#E8FF65',
    'accent_violet_dim': '#C4DC3B',
    'accent_cyan': '#82B9B1',
    'accent_cyan_dim': '#689790',

    # Scrollbars
    'scrollbar_bg': '#171918',
    'scrollbar_handle': '#303331',
    'scrollbar_hover': '#424744',
}


def get_global_stylesheet() -> str:
    """Returns the application-wide QSS stylesheet."""
    c = COLORS
    return f"""
    /* ===== Global Window & Widgets ===== */
    QMainWindow {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
    }}

    QWidget {{
        color: {c['text_primary']};
        font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
        font-size: 12px;
        background: transparent;
    }}

    /* ===== Scrollbars ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['scrollbar_handle']};
        min-height: 24px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        margin: 0;
        border-radius: 3px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['scrollbar_handle']};
        min-width: 24px;
        border-radius: 3px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        background: none;
    }}

    /* ===== Labels ===== */
    QLabel {{
        color: {c['text_primary']};
        background: transparent;
    }}

    /* ===== Primary Action Buttons ===== */
    QPushButton {{
        background-color: {c['bg_panel']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 600;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {c['bg_card_hover']};
        border-color: {c['border_light']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_selected']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_panel_alt']};
        border-color: {c['border_subtle']};
        color: {c['text_muted']};
    }}

    /* Primary Accent Button Variant (lime) */
    QPushButton[primary="true"], QPushButton.primary-btn {{
        background-color: {c['accent_lime']};
        color: {c['text_inverse']};
        border: 1px solid {c['accent_lime']};
        font-weight: 700;
    }}
    QPushButton[primary="true"]:hover, QPushButton.primary-btn:hover {{
        background-color: {c['accent_lime_dim']};
        border-color: {c['accent_lime_dim']};
    }}

    /* Danger Button Variant (red) */
    QPushButton[danger="true"], QPushButton.danger-btn {{
        background-color: #241617;
        color: {c['red']};
        border: 1px solid #4D2628;
        font-weight: 600;
    }}
    QPushButton[danger="true"]:hover, QPushButton.danger-btn:hover {{
        background-color: #331A1C;
        border-color: {c['red']};
    }}

    /* ===== Form Inputs ===== */
    QLineEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 7px 12px;
        font-size: 12px;
        selection-background-color: {c['accent_teal']};
        selection-color: {c['bg_primary']};
    }}
    QLineEdit:hover {{
        border-color: {c['border_light']};
    }}
    QLineEdit:focus {{
        border-color: {c['accent_lime']};
        background-color: #181C1A;
    }}

    /* ===== ComboBox ===== */
    QComboBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 12px;
    }}
    QComboBox:hover {{
        border-color: {c['border_light']};
    }}
    QComboBox:focus {{
        border-color: {c['accent_lime']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_panel']};
        color: {c['text_primary']};
        selection-background-color: {c['bg_selected']};
        selection-color: {c['accent_lime']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}

    /* ===== SpinBox ===== */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c['accent_lime']};
    }}

    /* ===== CheckBox ===== */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {c['border']};
        border-radius: 4px;
        background-color: {c['bg_input']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['border_light']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent_lime']};
        border-color: {c['accent_lime']};
        image: none;
    }}

    /* ===== Table Widget ===== */
    QTableWidget {{
        background-color: {c['bg_panel']};
        color: {c['text_primary']};
        gridline-color: transparent;
        border: 1px solid {c['border']};
        border-radius: 8px;
        font-size: 12px;
        outline: none;
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border-bottom: 1px solid {c['border_subtle']};
    }}
    QTableWidget::item:selected {{
        background-color: {c['bg_selected']};
        color: {c['text_primary']};
    }}
    QTableWidget::item:hover {{
        background-color: {c['bg_card_hover']};
    }}
    QHeaderView::section {{
        background-color: {c['bg_panel_alt']};
        color: {c['text_secondary']};
        border: none;
        border-bottom: 1px solid {c['border']};
        padding: 8px 10px;
        font-weight: 600;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* ===== Tab Widget (Linear Style) ===== */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background: {c['bg_panel']};
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {c['text_secondary']};
        border: none;
        border-bottom: 2px solid transparent;
        padding: 8px 16px;
        margin-right: 4px;
        font-weight: 600;
        font-size: 12px;
    }}
    QTabBar::tab:hover {{
        color: {c['text_primary']};
    }}
    QTabBar::tab:selected {{
        color: {c['accent_lime']};
        border-bottom: 2px solid {c['accent_lime']};
    }}

    /* ===== GroupBox ===== */
    QGroupBox {{
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 18px;
        font-weight: 600;
        font-size: 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {c['text_secondary']};
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* ===== Progress Bar ===== */
    QProgressBar {{
        background-color: {c['bg_panel_alt']};
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: center;
        font-size: 9px;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent_lime']};
        border-radius: 3px;
    }}

    /* ===== Tooltip ===== */
    QToolTip {{
        background-color: {c['bg_sidebar']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 5px 8px;
        font-size: 11px;
    }}

    /* ===== Message Box ===== */
    QMessageBox {{
        background-color: {c['bg_panel']};
        border: 1px solid {c['border']};
    }}
    QMessageBox QLabel {{
        color: {c['text_primary']};
        font-size: 12px;
    }}
    """


def card_style(extra: str = "") -> str:
    """Returns CSS for a standard technical panel."""
    c = COLORS
    return (
        f"background-color: {c['bg_panel']}; "
        f"border: 1px solid {c['border']}; "
        f"border-radius: 8px; "
        f"{extra}"
    )


def panel_alt_style(extra: str = "") -> str:
    """Returns CSS for an inset/secondary technical panel."""
    c = COLORS
    return (
        f"background-color: {c['bg_panel_alt']}; "
        f"border: 1px solid {c['border_subtle']}; "
        f"border-radius: 6px; "
        f"{extra}"
    )


def sidebar_button_style(active: bool = False) -> str:
    """Linear-style restrained sidebar navigation button."""
    c = COLORS
    if active:
        return (
            f"QPushButton {{ "
            f"background-color: {c['bg_selected']}; "
            f"color: {c['text_primary']}; "
            f"border: none; "
            f"border-left: 3px solid {c['accent_lime']}; "
            f"border-radius: 0px; "
            f"padding: 8px 14px; "
            f"text-align: left; "
            f"font-size: 13px; "
            f"font-weight: 600; "
            f"}}"
        )
    return (
        f"QPushButton {{ "
        f"background-color: transparent; "
        f"color: {c['text_secondary']}; "
        f"border: none; "
        f"border-left: 3px solid transparent; "
        f"border-radius: 0px; "
        f"padding: 8px 14px; "
        f"text-align: left; "
        f"font-size: 13px; "
        f"font-weight: 500; "
        f"}}"
        f"QPushButton:hover {{ "
        f"background-color: {c['bg_card_hover']}; "
        f"color: {c['text_primary']}; "
        f"}}"
    )


def sidebar_button_hover_style() -> str:
    c = COLORS
    return f"background-color: {c['bg_card_hover']}; color: {c['text_primary']};"


def severity_badge_style(severity: str) -> str:
    """Restrained severity badge styling with muted backgrounds and crisp text."""
    sev = severity.lower()
    if 'crit' in sev or 'error' in sev:
        bg = 'rgba(224, 82, 82, 0.12)'
        border = 'rgba(224, 82, 82, 0.35)'
        color = '#E05252'
    elif 'warn' in sev:
        bg = 'rgba(229, 169, 60, 0.12)'
        border = 'rgba(229, 169, 60, 0.35)'
        color = '#E5A93C'
    elif 'info' in sev:
        bg = 'rgba(164, 166, 159, 0.10)'
        border = 'rgba(164, 166, 159, 0.25)'
        color = '#A4A69F'
    else:  # healthy / nominal
        bg = 'rgba(130, 185, 177, 0.12)'
        border = 'rgba(130, 185, 177, 0.35)'
        color = '#82B9B1'

    return (
        f"background-color: {bg}; color: {color}; "
        f"border: 1px solid {border}; border-radius: 4px; "
        f"padding: 2px 7px; font-weight: 600; font-size: 10px; "
        f"font-family: 'Consolas', 'Segoe UI Mono', monospace; text-transform: uppercase;"
    )
