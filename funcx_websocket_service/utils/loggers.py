import logging


def set_stream_logger(name='funcx_websocket_service', level=logging.DEBUG, format_string=None):
     """Add a stream log handler.

     Args:
          - name (string) : Set the logger name.
          - level (logging.LEVEL) : Set to logging.DEBUG by default.
          - format_string (string) : Set to None by default.

     Returns:
          - None
     """

     logger = logging.getLogger(name)
     logger.setLevel(logging.DEBUG)
     handler = logging.StreamHandler()
     handler.setLevel(level)
     if format_string is not None:
          formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
          handler.setFormatter(formatter)
     logger.addHandler(handler)
     return logger
