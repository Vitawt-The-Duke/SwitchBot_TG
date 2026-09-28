import os
import gzip
import shutil
import logging
from logging.handlers import RotatingFileHandler
from app.config import settings


class CompressedRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that compresses rotated files into .gz archives."""

    def rotation_filename(self, default_name: str) -> str:
        if not default_name.endswith(".gz"):
            return default_name + ".gz"
        return default_name

    def rotate(self, source: str, dest: str) -> None:
        """Compress source to dest using gzip and remove source."""
        # Ensure destination directory exists
        dest_dir = os.path.dirname(dest)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)


def setup_logging(service_name: str = "switchbot", log_level: int = logging.INFO) -> None:
    """Configure root logger with console and compressed rotating file output."""
    log_dir = settings.log_dir
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{service_name}.log")

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid adding duplicate handlers on multiple setup calls
    for h in list(root_logger.handlers):
        if isinstance(h, (logging.StreamHandler, RotatingFileHandler)):
            try:
                h.close()
            except Exception:
                pass
            root_logger.removeHandler(h)

    # Console / stdout handler (for systemd journalctl & terminal)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)
    root_logger.addHandler(stream_handler)

    # 1 MB compressed rotating file handler (up to 4 .gz backups)
    file_handler = CompressedRotatingFileHandler(
        log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)
