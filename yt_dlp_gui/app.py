import sys
import qdarktheme

from PySide6.QtWidgets import QApplication

from yt_dlp_gui.config import get_assets_dir
from yt_dlp_gui.ui.main_window import MainWindow


BASE_QSS = """
QWidget {
    font-size: 10pt;
}

/* Main surfaces */
QMainWindow, QWidget {
    background-color: #20242b;
    color: #e6e6e6;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #4b4f58;
    border-radius: 10px;
    top: -1px;
    background: #252a33;
}

QTabBar::tab {
    background: #2b2f36;
    border: 1px solid #4b4f58;
    padding: 8px 14px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 120px;
}

QTabBar::tab:selected {
    background: #353b46;
    border-bottom-color: #353b46;
}

QTabBar::tab:hover {
    background: #313743;
}

/* Group boxes */
QGroupBox {
    font-weight: 600;
    border: 1px solid #4b4f58;
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 14px;
    background: #252a33;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* Text inputs */
QLineEdit, QTextEdit {
    background: #2b2f36;
    border: 1px solid #5a6070;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 22px;
    selection-background-color: #4c78d0;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #6ea8fe;
}

/* Combo boxes */
QComboBox {
    background: #2b2f36;
    border: 1px solid #5a6070;
    border-radius: 8px;
    padding: 8px 32px 8px 10px;
    min-height: 22px;
}

QComboBox:focus {
    border: 1px solid #6ea8fe;
}

QComboBox:hover {
    border: 1px solid #7a8296;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #5a6070;
    background: #313743;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

QComboBox QAbstractItemView {
    background: #2b2f36;
    border: 1px solid #5a6070;
    outline: 0;
    selection-background-color: #4c78d0;
    selection-color: #ffffff;
    padding: 4px;
}

/* Buttons */
QPushButton {
    background: #313743;
    border: 1px solid #5a6070;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
    min-height: 22px;
}

QPushButton:hover {
    border: 1px solid #6ea8fe;
    background: #394150;
}

QPushButton:pressed {
    background: #2a3040;
}

/* Checkboxes */
QCheckBox {
    spacing: 10px;
    color: #e6e6e6;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #8a92a3;
    border-radius: 4px;
    background: #262a31;
}

QCheckBox::indicator:hover {
    border: 1px solid #6ea8fe;
}

QCheckBox::indicator:checked {
    background: #6ea8fe;
    border: 1px solid #6ea8fe;
}

QCheckBox::indicator:unchecked {
    background: #262a31;
}

/* Progress bar */
QProgressBar {
    background: #2b2f36;
    border: 1px solid #5a6070;
    border-radius: 8px;
    text-align: center;
    min-height: 18px;
}

QProgressBar::chunk {
    background: #6ea8fe;
    border-radius: 7px;
}
"""


def build_stylesheet() -> str:
    arrow_svg = (get_assets_dir() / "icons" / "chevron-down.svg").resolve().as_posix()

    arrow_qss = f"""
QComboBox::down-arrow {{
    image: url("{arrow_svg}");
    width: 14px;
    height: 14px;
}}
"""
    return BASE_QSS + arrow_qss


def run() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarktheme.load_stylesheet() + build_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
