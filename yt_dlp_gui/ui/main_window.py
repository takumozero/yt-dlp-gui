from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from yt_dlp_gui.services import YtDlpRunner


class DropTextEdit(QTextEdit):
    def __init__(self, parent_window: "MainWindow") -> None:
        super().__init__()
        self.parent_window = parent_window
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        text = event.mimeData().text()
        self.parent_window.add_urls_from_text(text)
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.runner = YtDlpRunner()
        self.default_output_path = str(Path.home() / "Desktop")
        self.preview_data: dict | None = None
        self.current_preview_url: str | None = None
        self.is_downloading = False
        self.is_updating = False

        self.setWindowTitle("yt-dlp GUI")
        self.resize(1280, 860)

        self._build_ui()
        self._connect_runner_signals()
        self._update_mode_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        header_group = QGroupBox("Download Queue")
        header_layout = QGridLayout(header_group)
        header_layout.setHorizontalSpacing(10)
        header_layout.setVerticalSpacing(10)

        self.url_input = DropTextEdit(self)
        self.url_input.setPlaceholderText(
            "Paste one or more URLs here, one per line.\nYou can also drag and drop URLs into this box."
        )
        self.url_input.setMinimumHeight(100)

        self.output_input = QLineEdit()
        self.output_input.setText(self.default_output_path)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_output_folder)

        self.preview_button = QPushButton("Load Preview for Selected URL")
        self.preview_button.clicked.connect(self._load_preview)

        self.clear_urls_button = QPushButton("Clear URLs")
        self.clear_urls_button.clicked.connect(self.url_input.clear)

        self.update_button = QPushButton("Update yt-dlp")
        self.update_button.clicked.connect(self._start_update)

        header_layout.addWidget(QLabel("URLs"), 0, 0)
        header_layout.addWidget(self.url_input, 0, 1, 2, 3)

        header_layout.addWidget(QLabel("Output Folder"), 2, 0)
        header_layout.addWidget(self.output_input, 2, 1, 1, 2)
        header_layout.addWidget(self.browse_button, 2, 3)

        header_layout.addWidget(self.preview_button, 3, 1)
        header_layout.addWidget(self.clear_urls_button, 3, 2)
        header_layout.addWidget(self.update_button, 3, 3)

        header_layout.setColumnStretch(1, 1)
        header_layout.setColumnStretch(2, 1)

        root_layout.addWidget(header_group)

        preview_group = QGroupBox("Preview")
        preview_layout = QHBoxLayout(preview_group)

        self.thumbnail_label = QLabel("No thumbnail")
        self.thumbnail_label.setFixedSize(240, 135)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        preview_info_layout = QVBoxLayout()

        self.preview_title_label = QLabel("Title: -")
        self.preview_title_label.setWordWrap(True)

        self.preview_uploader_label = QLabel("Uploader: -")
        self.preview_duration_label = QLabel("Duration: -")
        self.preview_entries_label = QLabel("Entries: -")

        preview_info_layout.addWidget(self.preview_title_label)
        preview_info_layout.addWidget(self.preview_uploader_label)
        preview_info_layout.addWidget(self.preview_duration_label)
        preview_info_layout.addWidget(self.preview_entries_label)
        preview_info_layout.addStretch()

        preview_layout.addWidget(self.thumbnail_label)
        preview_layout.addLayout(preview_info_layout, 1)

        root_layout.addWidget(preview_group)

        center_layout = QHBoxLayout()
        center_layout.setSpacing(12)

        entries_group = QGroupBox("Items to Download")
        entries_layout = QVBoxLayout(entries_group)

        entries_button_row = QHBoxLayout()
        self.select_all_entries_button = QPushButton("Select All")
        self.select_all_entries_button.clicked.connect(self._select_all_entries)

        self.clear_entry_selection_button = QPushButton("Clear Selection")
        self.clear_entry_selection_button.clicked.connect(self._clear_entry_selection)

        entries_button_row.addWidget(self.select_all_entries_button)
        entries_button_row.addWidget(self.clear_entry_selection_button)
        entries_button_row.addStretch()

        self.entries_list = QListWidget()
        self.entries_list.setAlternatingRowColors(True)
        self.entries_list.setSpacing(4)
        self.entries_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        entries_font = QFont()
        entries_font.setPointSize(11)
        self.entries_list.setFont(entries_font)

        entries_layout.addLayout(entries_button_row)
        entries_layout.addWidget(self.entries_list)

        center_layout.addWidget(entries_group, 1)

        self.tabs = QTabWidget()
        self._build_basic_tab()
        self._build_media_tab()
        self._build_extra_tab()

        center_layout.addWidget(self.tabs, 1)

        root_layout.addLayout(center_layout, 1)

        button_row = QHBoxLayout()

        self.download_button = QPushButton("Download Queue")
        self.download_button.clicked.connect(self._start_download)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_download)
        self.cancel_button.setEnabled(False)

        button_row.addWidget(self.download_button)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch()

        root_layout.addLayout(button_row)

        status_group = QGroupBox("Status")
        status_layout = QGridLayout(status_group)

        self.current_file_label = QLabel("Current file: -")
        self.current_file_label.setWordWrap(True)

        self.playlist_progress_label = QLabel("Playlist: -")
        self.status_label = QLabel("Status: Idle")
        self.last_log_file_label = QLabel("Log file: -")
        self.last_log_file_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        status_layout.addWidget(self.current_file_label, 0, 0, 1, 2)
        status_layout.addWidget(self.playlist_progress_label, 1, 0)
        status_layout.addWidget(self.status_label, 1, 1)
        status_layout.addWidget(self.last_log_file_label, 2, 0, 1, 2)
        status_layout.addWidget(self.progress_bar, 3, 0, 1, 2)

        root_layout.addWidget(status_group)

    def _build_basic_tab(self) -> None:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Video", "Audio"])
        self.mode_combo.currentIndexChanged.connect(self._update_mode_ui)

        self.playlist_mode_combo = QComboBox()
        self.playlist_mode_combo.addItems([
            "Allow playlist downloads",
            "Download single item only",
        ])

        self.subtitle_mode_combo = QComboBox()
        self.subtitle_mode_combo.addItems([
            "None",
            "Download subtitles",
            "Download auto subtitles",
            "Embed subtitles if available",
            "Download and embed subtitles",
        ])

        layout.addWidget(QLabel("Mode"), 0, 0)
        layout.addWidget(self.mode_combo, 0, 1)

        layout.addWidget(QLabel("Playlist"), 0, 2)
        layout.addWidget(self.playlist_mode_combo, 0, 3)

        layout.addWidget(QLabel("Subtitles"), 1, 0)
        layout.addWidget(self.subtitle_mode_combo, 1, 1, 1, 3)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        self.tabs.addTab(tab, "Basic")

    def _build_media_tab(self) -> None:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(["Best", "MP4", "MKV", "WebM"])

        self.video_codec_combo = QComboBox()
        self.video_codec_combo.addItems(["Default", "H.264", "H.265", "VP9", "AV1"])

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["Best", "MP3", "M4A", "AAC", "Opus", "FLAC", "WAV"])

        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(["Best", "320k", "192k", "128k"])

        self.embed_thumbnail_checkbox = QCheckBox("Embed thumbnail")
        self.write_thumbnail_checkbox = QCheckBox("Write thumbnail file")
        self.keep_video_checkbox = QCheckBox("Keep video after audio extraction")

        layout.addWidget(QLabel("Video Format"), 0, 0)
        layout.addWidget(self.video_format_combo, 0, 1)

        layout.addWidget(QLabel("Video Codec"), 0, 2)
        layout.addWidget(self.video_codec_combo, 0, 3)

        layout.addWidget(QLabel("Audio Format"), 1, 0)
        layout.addWidget(self.audio_format_combo, 1, 1)

        layout.addWidget(QLabel("Audio Quality"), 1, 2)
        layout.addWidget(self.audio_quality_combo, 1, 3)

        layout.addWidget(self.embed_thumbnail_checkbox, 2, 0, 1, 2)
        layout.addWidget(self.write_thumbnail_checkbox, 2, 2, 1, 2)
        layout.addWidget(self.keep_video_checkbox, 3, 0, 1, 2)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        self.tabs.addTab(tab, "Media")

    def _build_extra_tab(self) -> None:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        self.split_chapters_checkbox = QCheckBox("Split video by chapters")
        self.embed_chapters_checkbox = QCheckBox("Embed chapters")
        self.write_description_checkbox = QCheckBox("Write description")
        self.write_info_json_checkbox = QCheckBox("Write info JSON")
        self.write_comments_checkbox = QCheckBox("Write comments")
        self.no_overwrites_checkbox = QCheckBox("Do not overwrite files")
        self.restrict_filenames_checkbox = QCheckBox("Restrict filenames")
        self.no_part_checkbox = QCheckBox("Do not use .part files")

        layout.addWidget(self.split_chapters_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.embed_chapters_checkbox, 0, 2, 1, 2)
        layout.addWidget(self.write_description_checkbox, 1, 0, 1, 2)
        layout.addWidget(self.write_info_json_checkbox, 1, 2, 1, 2)
        layout.addWidget(self.write_comments_checkbox, 2, 0, 1, 2)
        layout.addWidget(self.no_overwrites_checkbox, 2, 2, 1, 2)
        layout.addWidget(self.restrict_filenames_checkbox, 3, 0, 1, 2)
        layout.addWidget(self.no_part_checkbox, 3, 2, 1, 2)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        self.tabs.addTab(tab, "Extra")

    def _connect_runner_signals(self) -> None:
        self.runner.progress_changed.connect(self.progress_bar.setValue)
        self.runner.status_changed.connect(self._set_status_text)
        self.runner.current_file_changed.connect(self._set_current_file_text)
        self.runner.playlist_progress_changed.connect(self._set_playlist_progress_text)
        self.runner.download_finished.connect(self._on_download_finished)
        self.runner.update_finished.connect(self._on_update_finished)

    def add_urls_from_text(self, text: str) -> None:
        existing = set(self.get_urls())
        new_lines = []

        for line in text.splitlines():
            url = line.strip()
            if not url:
                continue
            if url not in existing:
                existing.add(url)
                new_lines.append(url)

        if not new_lines:
            return

        current = self.url_input.toPlainText().strip()
        if current:
            current += "\n"
        current += "\n".join(new_lines)
        self.url_input.setPlainText(current)

    def get_urls(self) -> list[str]:
        urls: list[str] = []
        for line in self.url_input.toPlainText().splitlines():
            url = line.strip()
            if url:
                urls.append(url)
        return urls

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.output_input.text(),
        )
        if folder:
            self.output_input.setText(folder)

    def _update_mode_ui(self) -> None:
        is_audio_mode = self.mode_combo.currentText() == "Audio"
        self.video_format_combo.setEnabled(not is_audio_mode)
        self.video_codec_combo.setEnabled(not is_audio_mode)
        self.keep_video_checkbox.setEnabled(is_audio_mode)

    def _collect_options(self) -> dict:
        subtitle_mode = self.subtitle_mode_combo.currentText()
        playlist_mode = self.playlist_mode_combo.currentText()

        return {
            "mode": self.mode_combo.currentText(),
            "video_format": self.video_format_combo.currentText(),
            "video_codec": self.video_codec_combo.currentText(),
            "audio_format": self.audio_format_combo.currentText(),
            "audio_quality": self.audio_quality_combo.currentText(),
            "allow_playlist": playlist_mode == "Allow playlist downloads",
            "write_subs": subtitle_mode in ("Download subtitles", "Download and embed subtitles"),
            "write_auto_subs": subtitle_mode == "Download auto subtitles",
            "embed_subs": subtitle_mode in ("Embed subtitles if available", "Download and embed subtitles"),
            "split_chapters": self.split_chapters_checkbox.isChecked(),
            "embed_chapters": self.embed_chapters_checkbox.isChecked(),
            "write_thumbnail": self.write_thumbnail_checkbox.isChecked(),
            "embed_thumbnail": self.embed_thumbnail_checkbox.isChecked(),
            "write_description": self.write_description_checkbox.isChecked(),
            "write_info_json": self.write_info_json_checkbox.isChecked(),
            "write_comments": self.write_comments_checkbox.isChecked(),
            "keep_video": self.keep_video_checkbox.isChecked(),
            "no_overwrites": self.no_overwrites_checkbox.isChecked(),
            "restrict_filenames": self.restrict_filenames_checkbox.isChecked(),
            "no_part": self.no_part_checkbox.isChecked(),
            "playlist_items": self._get_selected_playlist_items(),
        }

    def _get_selected_url_for_preview(self) -> str | None:
        urls = self.get_urls()
        if not urls:
            return None
        return urls[0]

    def _load_preview(self) -> None:
        url = self._get_selected_url_for_preview()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter at least one URL first.")
            return

        try:
            data = self.runner.load_preview(url)
            self.preview_data = data
            self.current_preview_url = url
            self._populate_preview(data)
        except Exception as exc:
            QMessageBox.critical(self, "Preview Error", str(exc))

    def _populate_preview(self, data: dict) -> None:
        title = data.get("title") or ""
        uploader = (
            data.get("artist")
            or data.get("album_artist")
            or data.get("uploader")
            or data.get("channel")
            or ""
        )
        duration = self._format_duration(data.get("duration"))
        entries = data.get("entries") or []

        if uploader:
            self.preview_title_label.setText(f"{title} - {uploader}")
        else:
            self.preview_title_label.setText(title)

        self.preview_uploader_label.setText("")
        self.preview_duration_label.setText(f"Duration: {duration}")
        self.preview_entries_label.setText(f"Entries: {len(entries) if entries else 1}")

        self._set_thumbnail(data.get("thumbnail"))
        self.entries_list.clear()

        if entries:
            for index, entry in enumerate(entries, start=1):
                item_text = self._format_preview_item_text(entry, index)
                item = QListWidgetItem(item_text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, index)
                self.entries_list.addItem(item)
        else:
            item_text = self._format_preview_item_text(data, 1)
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, 1)
            self.entries_list.addItem(item)

    def _format_preview_item_text(self, entry: dict, index: int) -> str:
        title = entry.get("title") or f"Item {index}"

        artist = (
            entry.get("artist")
            or entry.get("album_artist")
            or entry.get("uploader")
            or entry.get("channel")
            or ""
        )

        if artist:
            return f"{title} - {artist}"

        return title

    def _select_all_entries(self) -> None:
        for i in range(self.entries_list.count()):
            item = self.entries_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)

    def _clear_entry_selection(self) -> None:
        for i in range(self.entries_list.count()):
            item = self.entries_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)

    def _get_selected_playlist_items(self) -> str | None:
        if not self.preview_data:
            return None

        entries = self.preview_data.get("entries") or []
        if not entries:
            return None

        selected_indices: list[int] = []
        for i in range(self.entries_list.count()):
            item = self.entries_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                index = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(index, int):
                    selected_indices.append(index)

        if not selected_indices:
            return None

        if len(selected_indices) == len(entries):
            return None

        return ",".join(str(index) for index in selected_indices)

    def _set_thumbnail(self, thumbnail_url: str | None) -> None:
        if not thumbnail_url:
            self.thumbnail_label.setText("No thumbnail")
            self.thumbnail_label.setPixmap(QPixmap())
            return

        try:
            with urlopen(thumbnail_url, timeout=10) as response:
                image_data = response.read()

            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            scaled = pixmap.scaled(
                self.thumbnail_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumbnail_label.setPixmap(scaled)
            self.thumbnail_label.setText("")
        except Exception:
            self.thumbnail_label.setText("Thumbnail unavailable")
            self.thumbnail_label.setPixmap(QPixmap())

    def _format_duration(self, seconds: int | None) -> str:
        if not seconds:
            return "-"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02}:{secs:02}"
        return f"{minutes}:{secs:02}"

    def _start_download(self) -> None:
        urls = self.get_urls()
        output_path = self.output_input.text().strip() or self.default_output_path

        if not urls:
            QMessageBox.warning(self, "Missing URL", "Please enter at least one URL.")
            return

        if self.is_updating:
            QMessageBox.warning(self, "Update Running", "Please wait until the update finishes.")
            return

        options = self._collect_options()

        self.output_input.setText(output_path)
        self.progress_bar.setValue(0)
        self._set_status_text("Starting...")
        self._set_current_file_text("-")
        self._set_playlist_progress_text("-")
        self._set_log_file_text("Will be created when download starts")

        self._set_downloading_state(True)

        self.runner.start_download(
            urls=urls,
            output_path=output_path,
            options=options,
        )

        if self.runner.worker:
            self._set_log_file_text(str(self.runner.worker.log_file_path))

    def _start_update(self) -> None:
        if self.is_downloading:
            QMessageBox.warning(self, "Download Running", "Please wait until the download finishes.")
            return

        self.is_updating = True
        self.update_button.setEnabled(False)
        self._set_status_text("Updating yt-dlp...")

        self.runner.start_update()

    def _cancel_download(self) -> None:
        if not self.is_downloading:
            return
        self.runner.cancel_download()

    def _on_download_finished(self, success: bool, message: str) -> None:
        self._set_downloading_state(False)

        if success:
            QMessageBox.information(self, "Download Finished", message)
        else:
            QMessageBox.warning(self, "Download Stopped", message)

    def _on_update_finished(self, success: bool, message: str, log_file: str) -> None:
        self.is_updating = False
        self.update_button.setEnabled(True)

        if log_file:
            self._set_log_file_text(log_file)

        if success:
            self._set_status_text("yt-dlp updated")
            QMessageBox.information(self, "Update Finished", f"{message}\n\nLog file: {log_file}")
        else:
            self._set_status_text("Update failed")
            QMessageBox.warning(self, "Update Failed", f"{message}\n\nLog file: {log_file}")

    def _set_downloading_state(self, downloading: bool) -> None:
        self.is_downloading = downloading
        self.download_button.setEnabled(not downloading)
        self.preview_button.setEnabled(not downloading)
        self.cancel_button.setEnabled(downloading)
        self.update_button.setEnabled(not downloading and not self.is_updating)

    def _set_status_text(self, text: str) -> None:
        self.status_label.setText(f"Status: {text}")

    def _set_current_file_text(self, text: str) -> None:
        self.current_file_label.setText(f"Current file: {text}")

    def _set_playlist_progress_text(self, text: str) -> None:
        self.playlist_progress_label.setText(f"Playlist: {text}")

    def _set_log_file_text(self, text: str) -> None:
        self.last_log_file_label.setText(f"Log file: {text}")
