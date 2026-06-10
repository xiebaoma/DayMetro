from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / ".runtime" / "logs"
DEFAULT_LOG_FILE = "daymetro.log"

_CONFIGURED = False


def resolve_log_dir() -> Path:
    return Path(os.getenv("DAYMETRO_LOG_DIR", str(DEFAULT_LOG_DIR)))


def resolve_log_path() -> Path:
    return resolve_log_dir() / os.getenv("DAYMETRO_LOG_FILE", DEFAULT_LOG_FILE)


def configure_logging() -> Path:
    global _CONFIGURED

    log_path = resolve_log_path()
    if _CONFIGURED:
        return log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)
    level_name = os.getenv("DAYMETRO_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=int(os.getenv("DAYMETRO_LOG_MAX_BYTES", "1048576")),
        backupCount=int(os.getenv("DAYMETRO_LOG_BACKUP_COUNT", "5")),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [file_handler]

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(level)

    _CONFIGURED = True
    logging.getLogger("daymetro.logging").info("logging configured path=%s", log_path)
    return log_path


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
