import logging
import os
from logging.handlers import RotatingFileHandler
import sys

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging():
    logger = logging.getLogger()  # root logger
    if logger.hasHandlers():
        logger.handlers.clear()  # prevent duplicate logs
    logger.setLevel(logging.DEBUG)

    # Console log
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(console_handler)

    # File log
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=1024*1024,  # ~1MB per file
        backupCount=1,  # Keep last backupCount logs
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(file_handler)


    ### LOG EXCEPTION ###
    def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow Ctrl+C without logging
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = log_uncaught_exceptions


    ### LOGGING FOR LLM CALLS ###
    llm_logger = logging.getLogger("LLM")
    if llm_logger.hasHandlers():
        llm_logger.handlers.clear()  # prevent duplicate logs
    llm_logger.setLevel(logging.DEBUG)

    # File handler for LLM calls
    llm_file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "llm_calls.log"),
        maxBytes=1024*1024,  # ~1MB per file
        backupCount=1,  # Keep last backupCount logs
        encoding="utf-8",
    )
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    llm_file_handler.setFormatter(formatter)
    llm_logger.addHandler(llm_file_handler)