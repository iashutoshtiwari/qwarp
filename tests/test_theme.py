from unittest.mock import Mock

import pytest
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QColor, QPalette

from qwarp.core.state import WarpStateManager
from qwarp.ui.branding import GradientLabel
from qwarp.ui.combobox import AccentComboBox
from qwarp.ui.styles import (
    ACCENT_COLOR,
    ACCENT_GRADIENT_COLOR,
    ThemeColors,
    apply_application_theme,
    build_application_stylesheet,
)
from qwarp.ui.toggle import AnimatedToggle
from qwarp.ui.window import WarpWindow
from qwarp.utils.system import is_dark_mode
from tests.test_state import FakeEngine


def make_light_palette() -> QPalette:
    """Create a representative light desktop palette (e.g. Breeze Light / Adwaita Light)."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#eff0f1"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#232629"))
    p.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f7f7"))
    p.setColor(QPalette.ColorRole.Text, QColor("#232629"))
    p.setColor(QPalette.ColorRole.Button, QColor("#eff0f1"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#232629"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#3daee9"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor("#767676"))
    p.setColor(QPalette.ColorRole.Mid, QColor("#c0c0c0"))
    p.setColor(QPalette.ColorRole.Midlight, QColor("#e0e0e0"))
    p.setColor(QPalette.ColorRole.Dark, QColor("#909090"))

    dis = QPalette.ColorGroup.Disabled
    p.setColor(dis, QPalette.ColorRole.WindowText, QColor("#828282"))
    p.setColor(dis, QPalette.ColorRole.Text, QColor("#828282"))
    p.setColor(dis, QPalette.ColorRole.ButtonText, QColor("#828282"))
    p.setColor(dis, QPalette.ColorRole.Highlight, QColor("#9acfe8"))
    p.setColor(dis, QPalette.ColorRole.Mid, QColor("#d0d0d0"))
    return p


def make_dark_palette() -> QPalette:
    """Create a representative dark desktop palette (e.g. Breeze Dark / Catppuccin Mocha)."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#181825"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#cdd6f4"))
    p.setColor(QPalette.ColorRole.Base, QColor("#1e1e2e"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#313244"))
    p.setColor(QPalette.ColorRole.Text, QColor("#cdd6f4"))
    p.setColor(QPalette.ColorRole.Button, QColor("#313244"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#cdd6f4"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#b4befe"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#11111b"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor("#a6adc8"))
    p.setColor(QPalette.ColorRole.Mid, QColor("#41435a"))
    p.setColor(QPalette.ColorRole.Midlight, QColor("#585b70"))
    p.setColor(QPalette.ColorRole.Dark, QColor("#24273a"))
    p.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))

    dis = QPalette.ColorGroup.Disabled
    p.setColor(dis, QPalette.ColorRole.WindowText, QColor("#626488"))
    p.setColor(dis, QPalette.ColorRole.Text, QColor("#626488"))
    p.setColor(dis, QPalette.ColorRole.ButtonText, QColor("#626488"))
    p.setColor(dis, QPalette.ColorRole.Highlight, QColor("#41435a"))
    p.setColor(dis, QPalette.ColorRole.Mid, QColor("#41435a"))
    return p


def wcag_contrast(c1: QColor, c2: QColor) -> float:
    """Compute standard WCAG relative luminance contrast ratio."""

    def to_lin(val: float) -> float:
        return val / 12.92 if val <= 0.03928 else ((val + 0.055) / 1.055) ** 2.4

    l1 = 0.2126 * to_lin(c1.redF()) + 0.7152 * to_lin(c1.greenF()) + 0.0722 * to_lin(c1.blueF())
    l2 = 0.2126 * to_lin(c2.redF()) + 0.7152 * to_lin(c2.greenF()) + 0.0722 * to_lin(c2.blueF())
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


@pytest.fixture
def manager():
    val = WarpStateManager(FakeEngine(), start_polling=False)
    yield val
    val.shutdown()


# ======================================================================
# A. Application Theme Setup Tests
# ======================================================================


def test_theme_setup_does_not_force_fusion_or_dark_palette():
    """Startup must retain the desktop platform's style and palette."""
    app = Mock()
    app.style.return_value = Mock()
    existing_palette = QPalette()
    app.palette.return_value = existing_palette

    apply_application_theme(app)

    app.setStyle.assert_not_called()
    app.setPalette.assert_not_called()
    app.setStyleSheet.assert_called_once()


def test_theme_setup_stylesheet_is_minimal_and_avoids_global_overrides():
    """Verify standard controls are free of hardcoded dark QSS."""
    stylesheet = build_application_stylesheet(make_light_palette())

    # Generic controls must NOT be globally overridden
    assert "QWidget {" not in stylesheet
    assert "QToolTip {" not in stylesheet
    assert "QLineEdit {" not in stylesheet
    assert "QComboBox {" not in stylesheet
    assert "QSpinBox {" not in stylesheet
    assert "QTabWidget {" not in stylesheet
    assert "QMenu {" not in stylesheet
    assert "#222222" not in stylesheet


# ======================================================================
# B. Palette Compatibility Tests
# ======================================================================


def test_palette_light_and_dark_classification():
    light_p = make_light_palette()
    dark_p = make_dark_palette()

    assert not is_dark_mode(light_p)
    assert is_dark_mode(dark_p)


def test_theme_colors_contrast_in_light_and_dark_modes():
    """Verify semantic text colors maintain adequate contrast against window background."""
    light_p = make_light_palette()
    dark_p = make_dark_palette()

    light_colors = ThemeColors.from_palette(light_p)
    dark_colors = ThemeColors.from_palette(dark_p)

    light_bg = light_p.color(QPalette.ColorRole.Window)
    dark_bg = dark_p.color(QPalette.ColorRole.Window)

    # In light mode, connected blue, mode blue, and error red must contrast >= 4.5:1
    assert wcag_contrast(QColor(light_colors.text_connected), light_bg) >= 4.5
    assert wcag_contrast(QColor(light_colors.text_mode), light_bg) >= 4.5
    assert wcag_contrast(QColor(light_colors.text_error), light_bg) >= 4.5

    # In dark mode, connected, mode, and error text must contrast >= 3.5:1
    assert wcag_contrast(QColor(dark_colors.text_connected), dark_bg) >= 3.5
    assert wcag_contrast(QColor(dark_colors.text_mode), dark_bg) >= 5.0
    assert wcag_contrast(QColor(dark_colors.text_error), dark_bg) >= 4.0


# ======================================================================
# C. AnimatedToggle Tests
# ======================================================================


def test_animated_toggle_derives_colors_from_light_and_dark_palettes(qapp):
    light_p = make_light_palette()
    dark_p = make_dark_palette()

    toggle = AnimatedToggle()

    # --- Light Palette ---
    toggle.setPalette(light_p)
    toggle.setChecked(True)
    toggle.setEnabled(True)
    assert toggle._get_track_color() == light_p.color(QPalette.ColorRole.Highlight)
    assert toggle._get_thumb_color() == light_p.color(QPalette.ColorRole.HighlightedText)

    toggle.setChecked(False)
    assert toggle._get_track_color() == light_p.color(QPalette.ColorRole.Mid)
    assert toggle._get_thumb_color() == light_p.color(QPalette.ColorRole.Base)

    toggle.setEnabled(False)
    dis = QPalette.ColorGroup.Disabled
    assert toggle._get_track_color() == light_p.color(dis, QPalette.ColorRole.Mid)

    # --- Dark Palette ---
    toggle.setPalette(dark_p)
    toggle.setEnabled(True)
    toggle.setChecked(True)
    assert toggle._get_track_color() == dark_p.color(QPalette.ColorRole.Highlight)
    assert toggle._get_thumb_color() == dark_p.color(QPalette.ColorRole.HighlightedText)

    toggle.setChecked(False)
    assert toggle._get_track_color() == dark_p.color(QPalette.ColorRole.Mid)
    dark_thumb = toggle._get_thumb_color()
    assert dark_thumb.lightness() > 100

    toggle.setEnabled(False)
    assert toggle._get_track_color() == dark_p.color(dis, QPalette.ColorRole.Mid)

    toggle.deleteLater()


def test_animated_toggle_render_and_focus(qapp):
    toggle = AnimatedToggle()
    toggle.resize(100, 50)

    # Unchecked render
    img = toggle.grab().toImage()
    assert not img.isNull()

    # Checked render
    toggle.setChecked(True)
    img_checked = toggle.grab().toImage()
    assert not img_checked.isNull()

    # Disabled render
    toggle.setEnabled(False)
    img_disabled = toggle.grab().toImage()
    assert not img_disabled.isNull()

    # Focus render
    toggle.setEnabled(True)
    toggle.setFocus()
    img_focused = toggle.grab().toImage()
    assert not img_focused.isNull()

    toggle.deleteLater()


# ======================================================================
# D. AccentComboBox Tests
# ======================================================================


def test_accent_combobox_derives_chevron_from_palette(qapp):
    combo = AccentComboBox()
    combo.addItem("WARP")
    combo.resize(200, 32)

    # --- Light Palette ---
    light_p = make_light_palette()
    combo.setPalette(light_p)
    combo.setEnabled(True)

    img = combo.grab().toImage()
    colors = {img.pixelColor(x, y).name() for x in range(img.width() - 28, img.width()) for y in range(img.height())}
    expected_light_text = light_p.color(QPalette.ColorRole.Text).name()
    assert expected_light_text in colors

    # --- Disabled in Light Palette ---
    combo.setEnabled(False)
    img_dis = combo.grab().toImage()
    colors_dis = {
        img_dis.pixelColor(x, y).name()
        for x in range(img_dis.width() - 28, img_dis.width())
        for y in range(img_dis.height())
    }
    expected_dis_color = light_p.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name()
    assert expected_dis_color in colors_dis

    # --- Dark Palette ---
    dark_p = make_dark_palette()
    combo.setPalette(dark_p)
    combo.setEnabled(True)

    img_dark = combo.grab().toImage()
    colors_dark = {
        img_dark.pixelColor(x, y).name()
        for x in range(img_dark.width() - 28, img_dark.width())
        for y in range(img_dark.height())
    }
    expected_dark_text = dark_p.color(QPalette.ColorRole.Text).name()
    assert expected_dark_text in colors_dark

    combo.deleteLater()


# ======================================================================
# E. Branding Identity Tests
# ======================================================================


def test_branding_identity_preserved(qapp):
    lbl = GradientLabel("QWARP")
    lbl.resize(200, 60)

    assert lbl.gradient_start.name() == ACCENT_COLOR
    assert lbl.gradient_end.name() == ACCENT_GRADIENT_COLOR
    assert ACCENT_COLOR == "#2f80ed"
    assert ACCENT_GRADIENT_COLOR == "#56ccf2"

    img = lbl.grab().toImage()
    assert not img.isNull()

    lbl.deleteLater()


# ======================================================================
# F. Runtime Palette Change Tests
# ======================================================================


def test_runtime_theme_update_without_restarting_state(qapp, manager):
    window = WarpWindow(manager)
    window.resize(340, 480)

    # Initial state
    assert window.manager is manager
    assert not window.header_label.grab().isNull()

    # Simulate runtime palette change (e.g. user toggles dark mode in KDE settings)
    light_p = make_light_palette()
    window.setPalette(light_p)
    event = QEvent(QEvent.Type.ApplicationPaletteChange)
    window.changeEvent(event)

    # UI updates cleanly without affecting manager or state
    assert window.manager is manager
    assert not window.header_label.grab().isNull()
    assert not window.settings_btn.icon().isNull()

    window.deleteLater()
