import sys

from PySide6.QtWidgets import QApplication

from yt_dlp_gui.ui.main_window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
