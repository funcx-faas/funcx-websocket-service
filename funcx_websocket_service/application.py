import os
import argparse
import logging
from funcx_websocket_service.server import WebSocketServer
from funcx_websocket_service.utils.loggers import set_stream_logger

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Debug logging")

    args = parser.parse_args()

    env_debug = os.environ.get('FUNCX_WEBSOCKET_SERVICE_DEBUG')

    debug = args.debug is True or env_debug is not None
    set_stream_logger(level=logging.DEBUG if debug else logging.INFO)

    run()


def run():
    logger = logging.getLogger(__name__)

    REDIS_HOST = os.environ.get('REDIS_HOST')
    if not REDIS_HOST:
        REDIS_HOST = os.environ.get('FUNCX_REDIS_MASTER_SERVICE_HOST')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
    if not RABBITMQ_HOST:
        RABBITMQ_HOST = os.environ.get('FUNCX_RABBITMQ_SERVICE_HOST')

    WEB_SERVICE_URI = os.environ.get('WEB_SERVICE_URI')

    if REDIS_HOST is None:
        REDIS_HOST = '127.0.0.1'

    if REDIS_PORT is None:
        REDIS_PORT = 6379

    if RABBITMQ_HOST is None:
        RABBITMQ_HOST = '127.0.0.1'

    if WEB_SERVICE_URI is None:
        WEB_SERVICE_URI = 'http://127.0.0.1:5000'

    logger.info('Starting WebSocket Server')
    logger.debug(f'Using redis host: {REDIS_HOST}, redis port: {REDIS_PORT}, RabbitMQ host: {RABBITMQ_HOST}, web service URI: {WEB_SERVICE_URI}')

    WebSocketServer(REDIS_HOST, REDIS_PORT, RABBITMQ_HOST, WEB_SERVICE_URI)

if __name__ == '__main__':
    cli()
