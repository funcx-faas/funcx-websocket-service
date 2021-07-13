import logging
from pythonjsonlogger import jsonlogger


def set_stream_logger(name='funcx_websocket_service', level=logging.DEBUG):
    """Add a stream log handler.

    Args:
        - name (string) : Set the logger name.
        - level (logging.LEVEL) : Set to logging.DEBUG by default.

    Returns:
        - Logger
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
