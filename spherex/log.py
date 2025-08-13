import logging


def get_logger(level=logging.INFO) -> logging.Logger:
    """
    Get a logger for the spherex package.

    :return: Logger instance
    """
    logger = logging.getLogger("spherex")
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level=level)
    return logger
