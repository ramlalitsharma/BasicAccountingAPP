import logging
import logging.handlers
import os
import sys
from pathlib import Path


def setup_logging(log_dir=None):
    if log_dir is None:
        if getattr(sys, "frozen", False):
            base = Path(os.path.dirname(sys.executable))
        else:
            base = Path(__file__).parent.parent
        log_dir = base / "logs"
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for h in root.handlers[:]:
        root.removeHandler(h)

    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "accounting.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    logging.info("=" * 50)
    logging.info("Application started")
    return logging.getLogger(__name__)
