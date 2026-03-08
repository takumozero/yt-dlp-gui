from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from yt_dlp_gui.services import YtDlpRunner


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.runner = YtDlpRunner()

        self.setWindowTitle("yt-dlp GUI")
        self.resize(900, 600)

        self.url_input: QLineEdit
        self.output_input: QLineEdit
        self.format_combo: QComboBox
        self.audio_only_checkbox: QCheckBox
        self.download_button: QPushButton
        self.cancel_button: QPushButton
        self.progress_bar: QProgressBar
        self.log_output: QPlainTextEdit

        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        settings_group = QGroupBox("Download Settings")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setHorizontalSpacing(10)
        settings_layout.setVerticalSpacing(10)

        url_label = QLabel("Video URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a video or playlist URL here")

        output_label = QLabel("Output Folder:")
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Choose where downloaded files should be saved")

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_output_folder)

        format_label = QLabel("Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "best",
            "bestvideo+bestaudio/best",
            "mp4",
            "mp3",
        ])

        self.audio_only_checkbox = QCheckBox("Audio only")

        settings_layout.addWidget(url_label, 0, 0)
        settings_layout.addWidget(self.url_input, 0, 1, 1, 2)

        settings_layout.addWidget(output_label, 1, 0)
        settings_layout.addWidget(self.output_input, 1, 1)
        settings_layout.addWidget(browse_button, 1, 2)

        settings_layout.addWidget(format_label, 2, 0)
        settings_layout.addWidget(self.format_combo, 2, 1)
        settings_layout.addWidget(self.audio_only_checkbox, 2, 2)

        settings_layout.setColumnStretch(1, 1)

        main_layout.addWidget(settings_group)

        button_layout = QHBoxLayout()

        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self._start_download)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_download)

        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        log_label = QLabel("Log Output:")
        main_layout.addWidget(log_label)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.log_output)

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_input.setText(folder)

    def _start_download(self) -> None:
        url = self.url_input.text().strip()
        output_path = self.output_input.text().strip()
        format_code = self.format_combo.currentText().strip()
        audio_only = self.audio_only_checkbox.isChecked()

        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a video URL.")
            return

        if not output_path:
            QMessageBox.warning(self, "Missing Output Folder", "Please select an output folder.")
            return

        self._append_log("Starting download...")
        self._append_log(f"URL: {url}")
        self._append_log(f"Output: {output_path}")
        self._append_log(f"Format: {format_code}")
        self._append_log(f"Audio only: {audio_only}")
        self._append_log("")

        self.progress_bar.setValue(10)

        self.runner.start_download(
            url=url,
            output_path=output_path,
            format_code=format_code,
            audio_only=audio_only,
        )

        self.progress_bar.setValue(100)
        self._append_log("Download command placeholder executed.")

    def _cancel_download(self) -> None:
        self.runner.cancel_download()
        self._append_log("Download cancelled.")
        self.progress_bar.setValue(0)

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)
