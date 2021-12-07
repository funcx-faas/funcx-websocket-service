import argparse
import logging
import os
import sys

from funcx_websocket_service.server import WebSocketServer
from funcx_websocket_service.utils.loggers import set_stream_logger

logger = logging.getLogger(__name__)


def cli():
    """CLI entrypoint for WebSocket server that takes CLI args, gathers env vars,
    and starts the WebSocket server
    """
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--debug", action="store_true", help="Debug logging")

        args = parser.parse_args()

        env_debug = os.environ.get("FUNCX_WEBSOCKET_SERVICE_DEBUG")

        debug = args.debug is True or env_debug is not None
        global logger
        logger = set_stream_logger(level=logging.DEBUG if debug else logging.INFO)

        REDIS_HOST = os.environ.get("REDIS_HOST")
        if not REDIS_HOST:
            REDIS_HOST = os.environ.get("FUNCX_REDIS_MASTER_SERVICE_HOST")
        REDIS_PORT = os.environ.get("REDIS_PORT")

        RABBITMQ_URI = os.environ.get("RABBITMQ_URI")
        if not RABBITMQ_URI:
            rabbitmq_host = os.environ.get("FUNCX_RABBITMQ_SERVICE_HOST", "127.0.0.1")
            RABBITMQ_URI = f"amqp://funcx:rabbitmq@{rabbitmq_host}/"

        WEB_SERVICE_URI = os.environ.get("WEB_SERVICE_URI")

        if REDIS_HOST is None:
            REDIS_HOST = "127.0.0.1"

        if REDIS_PORT is None:
            REDIS_PORT = 6379

        if WEB_SERVICE_URI is None:
            WEB_SERVICE_URI = "http://127.0.0.1:5000"

        logger.info("Starting WebSocket Server")
        logger.debug(
            f"Using redis host: {REDIS_HOST}, redis port: {REDIS_PORT}, "
            f"RabbitMQ uri: {RABBITMQ_URI}, web service URI: {WEB_SERVICE_URI}"
        )

        WebSocketServer(
            REDIS_HOST,
            REDIS_PORT,
            RABBITMQ_URI,
            WEB_SERVICE_URI,
        )
    except Exception:
        logger.exception("Caught exception while starting server")
        # log env variables, as the vars that are passed in are likely the reason
        # for server start failing
        logger.critical(os.environ)
        sys.exit(-1)
