class YtDlpRunner:
    def __init__(self) -> None:
        self.is_running = False

    def start_download(self, url: str, output_path: str, format_code: str, audio_only: bool) -> None:
        self.is_running = True

    def cancel_download(self) -> None:
        self.is_running = False
