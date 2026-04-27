"""Sistema de logging do bot."""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "wyd_bot",
    level: int = logging.INFO,
    log_file: str | None = None,
) -> logging.Logger:
    """Configura e retorna um logger.

    Args:
        name: Nome do logger.
        level: Nível de logging.
        log_file: Caminho opcional para arquivo de log.

    Returns:
        Logger configurado.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
