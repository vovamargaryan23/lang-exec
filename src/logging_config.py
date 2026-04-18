import logging
import logging.config

_CONSOLE_ONLY_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}

_FILE_CONFIG = {
    **_CONSOLE_ONLY_CONFIG,
    "handlers": {
        **_CONSOLE_ONLY_CONFIG["handlers"],
        "file": {
            # WatchedFileHandler re-opens the file after each rotation,
            # making it safe to use across multiple worker processes.
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "standard",
            "filename": "logs/app.log",
            "encoding": "utf-8",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}


def setup_logging() -> None:
    import os
    try:
        os.makedirs("logs", exist_ok=True)
        logging.config.dictConfig(_FILE_CONFIG)
    except Exception:
        logging.config.dictConfig(_CONSOLE_ONLY_CONFIG)
