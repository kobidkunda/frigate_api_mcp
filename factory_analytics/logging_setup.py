from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from factory_analytics.config import LOG_ROOT, LOG_LEVEL


def setup_logging() -> logging.Logger:
    logger = logging.getLogger('factory_analytics')
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    fh = RotatingFileHandler(LOG_ROOT / 'worker.log', maxBytes=2_000_000, backupCount=3)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger
