from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal
from yt_dlp_gui.config import get_logs_dir, get_yt_dlp_path
from yt_dlp_gui.config import get_ffmpeg_bin_dir


class UpdateWorker(QObject):
    finished = Signal(bool, str, str)

    def __init__(self, exe_path: Path) -> None:
        super().__init__()
        self.exe_path = exe_path

        self.logs_dir = get_logs_dir()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file_path = self.logs_dir / f"{timestamp}_update.log"

    def run(self) -> None:
        cmd = [str(self.exe_path), "-U"]

        self._write_log("Starting yt-dlp update...")
        self._write_log("Command:")
        self._write_log(" ".join(f'"{part}"' if " " in part else part for part in cmd))
        self._write_log("")

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                **_get_hidden_startup_kwargs(),
            )
        except Exception as exc:
            message = f"Failed to start updater: {exc}"
            self._write_log(message)
            self.finished.emit(False, message, str(self.log_file_path))
            return

        output = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
        output = output.strip()

        if output:
            self._write_log(output)

        if completed.returncode == 0:
            message = "yt-dlp update completed."
            self.finished.emit(True, message, str(self.log_file_path))
        else:
            message = f"yt-dlp update failed with exit code {completed.returncode}."
            self.finished.emit(False, message, str(self.log_file_path))

    def _write_log(self, text: str) -> None:
        with self.log_file_path.open("a", encoding="utf-8") as log_file:
            log_file.write(text + "\n")


class DownloadWorker(QObject):
    progress = Signal(int)
    status = Signal(str)
    current_file = Signal(str)
    playlist_progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        exe_path: Path,
        urls: list[str],
        output_path: str,
        options: dict[str, Any],
    ) -> None:
        super().__init__()
        self.exe_path = exe_path
        self.urls = urls
        self.output_path = output_path
        self.options = options
        self.process: subprocess.Popen[str] | None = None
        self._cancel_requested = False

        self.logs_dir = get_logs_dir()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file_path = self.logs_dir / f"{timestamp}.log"

    def run(self) -> None:
        total_urls = len(self.urls)

        for url_index, url in enumerate(self.urls, start=1):
            if self._cancel_requested:
                break

            self.status.emit(f"Queue item {url_index} / {total_urls}")
            ok = self._run_single_url(url)

            if not ok and self._cancel_requested:
                break

        if self._cancel_requested:
            self.progress.emit(0)
            self.status.emit("Cancelled")
            self.finished.emit(False, f"Download cancelled. Log file: {self.log_file_path}")
            return

        self.progress.emit(100)
        self.status.emit("Finished")
        self.finished.emit(True, f"Download finished successfully. Log file: {self.log_file_path}")

    def _run_single_url(self, url: str) -> bool:
        cmd = self._build_command(url)

        self._write_log("=" * 80)
        self._write_log(f"Starting URL: {url}")
        self._write_log("Command:")
        self._write_log(" ".join(f'"{part}"' if " " in part else part for part in cmd))
        self._write_log("")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **_get_hidden_startup_kwargs(),
            )
        except Exception as exc:
            self._write_log(f"Failed to start yt-dlp: {exc}")
            self.finished.emit(False, f"Failed to start yt-dlp: {exc}")
            return False

        assert self.process.stdout is not None

        for raw_line in self.process.stdout:
            line = raw_line.rstrip("\n\r")
            if not line:
                continue

            self._write_log(line)
            self._parse_progress_line(line)

            if self._cancel_requested:
                break

        return_code = self.process.wait()

        if self._cancel_requested:
            return False

        if return_code != 0:
            self._write_log(f"yt-dlp exited with code {return_code} for URL: {url}")
            self.finished.emit(False, f"yt-dlp exited with code {return_code}. Log file: {self.log_file_path}")
            return False

        return True

    def cancel(self) -> None:
        self._cancel_requested = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass

    def _write_log(self, text: str) -> None:
        with self.log_file_path.open("a", encoding="utf-8") as log_file:
            log_file.write(text + "\n")

    def _build_command(self, url: str) -> list[str]:
        base_template = "%(title)s - %(artist,uploader,channel)s.%(ext)s"
        chapter_template = "%(section_title)s.%(ext)s"

        ffmpeg_dir = get_ffmpeg_bin_dir()

        cmd = [
            str(self.exe_path),
            "--newline",
            "--progress",
            "--trim-filenames",
            "200",
            "--ffmpeg-location",
            str(ffmpeg_dir),
            "-P",
            self.output_path,
            "-o",
            base_template,
            "-o",
            f"pl_video:{base_template}",
            "-o",
            f"chapter:{chapter_template}",
        ]

        mode = self.options.get("mode", "Video")
        video_format = self.options.get("video_format", "Best")
        video_codec = self.options.get("video_codec", "Default")
        audio_format = self.options.get("audio_format", "Best")
        audio_quality = self.options.get("audio_quality", "Best")

        if mode == "Audio":
            cmd.append("-x")

            if audio_format != "Best":
                cmd.extend(["--audio-format", self._map_audio_format(audio_format)])

            if audio_quality != "Best":
                cmd.extend(["--audio-quality", audio_quality.replace("k", "")])

            if self.options.get("keep_video"):
                cmd.append("--keep-video")
        else:
            format_selector = self._build_video_format_selector(video_format, video_codec)
            cmd.extend(["-f", format_selector])

            merge_format = self._map_merge_output_format(video_format)
            if merge_format:
                cmd.extend(["--merge-output-format", merge_format])

        if self.options.get("allow_playlist"):
            cmd.append("--yes-playlist")
        else:
            cmd.append("--no-playlist")

        playlist_items = self.options.get("playlist_items")
        if playlist_items:
            cmd.extend(["--playlist-items", playlist_items])

        if self.options.get("split_chapters"):
            cmd.append("--split-chapters")

        if self.options.get("embed_chapters"):
            cmd.append("--embed-chapters")

        if self.options.get("write_subs"):
            cmd.append("--write-subs")

        if self.options.get("write_auto_subs"):
            cmd.append("--write-auto-subs")

        if self.options.get("embed_subs"):
            cmd.append("--embed-subs")

        if self.options.get("write_thumbnail"):
            cmd.append("--write-thumbnail")

        if self.options.get("embed_thumbnail"):
            cmd.append("--embed-thumbnail")

        if self.options.get("write_description"):
            cmd.append("--write-description")

        if self.options.get("write_info_json"):
            cmd.append("--write-info-json")

        if self.options.get("write_comments"):
            cmd.append("--write-comments")

        if self.options.get("no_overwrites"):
            cmd.append("--no-overwrites")

        if self.options.get("restrict_filenames"):
            cmd.append("--restrict-filenames")

        if self.options.get("no_part"):
            cmd.append("--no-part")

        cmd.append(url)
        return cmd

    def _build_video_format_selector(self, video_format: str, video_codec: str) -> str:
        extension_map = {
            "Best": None,
            "MP4": "mp4",
            "MKV": "mkv",
            "WebM": "webm",
        }

        codec_map = {
            "Default": None,
            "H.264": "avc1",
            "H.265": "hevc|h265",
            "VP9": "vp9",
            "AV1": "av01",
        }

        ext = extension_map.get(video_format)
        codec = codec_map.get(video_codec)

        video_filters: list[str] = []
        if ext:
            video_filters.append(f"ext={ext}")
        if codec:
            video_filters.append(f"vcodec~='({codec})'")

        if video_filters:
            return f"bestvideo[{']['.join(video_filters)}]+bestaudio/best"
        return "bestvideo+bestaudio/best"

    def _map_merge_output_format(self, video_format: str) -> str | None:
        mapping = {
            "MP4": "mp4",
            "MKV": "mkv",
            "WebM": "webm",
        }
        return mapping.get(video_format)

    def _map_audio_format(self, audio_format: str) -> str:
        mapping = {
            "MP3": "mp3",
            "M4A": "m4a",
            "AAC": "aac",
            "Opus": "opus",
            "FLAC": "flac",
            "WAV": "wav",
        }
        return mapping.get(audio_format, "best")

    def _parse_progress_line(self, line: str) -> None:
        playlist_match = re.search(r"\[download\]\s+Downloading item\s+(\d+)\s+of\s+(\d+)", line)
        if playlist_match:
            current = playlist_match.group(1)
            total = playlist_match.group(2)
            self.playlist_progress.emit(f"Playlist item {current} / {total}")
            return

        percent_match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
        if percent_match:
            try:
                percent = int(float(percent_match.group(1)))
                self.progress.emit(max(0, min(100, percent)))
            except ValueError:
                pass

            eta_match = re.search(r"ETA\s+([0-9:]+)", line)
            speed_match = re.search(r"at\s+([^\s]+)", line)

            status_parts = []
            if speed_match:
                status_parts.append(speed_match.group(1))
            if eta_match:
                status_parts.append(f"ETA {eta_match.group(1)}")

            if status_parts:
                self.status.emit(" | ".join(status_parts))
            return

        destination_patterns = [
            r"\[download\]\s+Destination:\s+(.+)",
            r"\[Merger\]\s+Merging formats into\s+\"(.+)\"",
            r"\[ExtractAudio\]\s+Destination:\s+(.+)",
        ]

        for pattern in destination_patterns:
            match = re.search(pattern, line)
            if match:
                self.current_file.emit(match.group(1).strip().strip('"'))
                return


class YtDlpRunner(QObject):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    current_file_changed = Signal(str)
    playlist_progress_changed = Signal(str)
    download_finished = Signal(bool, str)
    update_finished = Signal(bool, str, str)

    def __init__(self) -> None:
        super().__init__()
        self.thread: QThread | None = None
        self.worker: DownloadWorker | None = None

        self.update_thread: QThread | None = None
        self.update_worker: UpdateWorker | None = None

    def _get_yt_dlp_exe(self) -> Path:
        return get_yt_dlp_path()

    def load_preview(self, url: str) -> dict[str, Any]:
        exe_path = self._get_yt_dlp_exe()

        if not exe_path.exists():
            raise FileNotFoundError(f"yt-dlp.exe not found: {exe_path}")

        cmd = [str(exe_path), "-J", "--flat-playlist", url]

        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **_get_hidden_startup_kwargs(),
        )

        if completed.returncode != 0:
            error_text = completed.stdout or completed.stderr or "Failed to load preview."
            raise RuntimeError(error_text.strip())

        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse preview JSON: {exc}") from exc

    def start_download(self, urls: list[str], output_path: str, options: dict[str, Any]) -> None:
        exe_path = self._get_yt_dlp_exe()

        if not exe_path.exists():
            self.download_finished.emit(False, f"yt-dlp.exe not found: {exe_path}")
            return

        if self.thread and self.thread.isRunning():
            self.download_finished.emit(False, "A download is already running.")
            return

        self.thread = QThread()
        self.worker = DownloadWorker(exe_path, urls, output_path, options)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.progress.connect(self.progress_changed)
        self.worker.status.connect(self.status_changed)
        self.worker.current_file.connect(self.current_file_changed)
        self.worker.playlist_progress.connect(self.playlist_progress_changed)
        self.worker.finished.connect(self._on_worker_finished)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def start_update(self) -> None:
        exe_path = self._get_yt_dlp_exe()

        if not exe_path.exists():
            self.update_finished.emit(False, f"yt-dlp.exe not found: {exe_path}", "")
            return

        if self.thread and self.thread.isRunning():
            self.update_finished.emit(False, "Cannot update while a download is running.", "")
            return

        if self.update_thread and self.update_thread.isRunning():
            self.update_finished.emit(False, "An update is already running.", "")
            return

        self.update_thread = QThread()
        self.update_worker = UpdateWorker(exe_path)
        self.update_worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.finished.connect(self._on_update_worker_finished)

        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)

        self.update_thread.start()

    def cancel_download(self) -> None:
        if self.worker:
            self.worker.cancel()

    def _on_worker_finished(self, success: bool, message: str) -> None:
        self.download_finished.emit(success, message)
        self.worker = None
        self.thread = None

    def _on_update_worker_finished(self, success: bool, message: str, log_file: str) -> None:
        self.update_finished.emit(success, message, log_file)
        self.update_worker = None
        self.update_thread = None

def _get_hidden_startup_kwargs() -> dict:
    if sys.platform != "win32":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE

    return {
        "startupinfo": startupinfo,
        "creationflags": subprocess.CREATE_NO_WINDOW,
    }
