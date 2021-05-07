import os
import logging
from funcx_ws.server import WebSocketServer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)


def run():
    REDIS_HOST = os.environ.get('REDIS_HOST')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    RABBITMQ_HOST = os.environ.get('FUNCX_RABBITMQ_SERVICE_HOST')
    WEB_SERVICE_HOST = os.environ.get('WEB_SERVICE_HOST')

    if REDIS_HOST is None:
        REDIS_HOST = '127.0.0.1'

    if REDIS_PORT is None:
        REDIS_PORT = 6379

    if RABBITMQ_HOST is None:
        RABBITMQ_HOST = '127.0.0.1'

    if WEB_SERVICE_HOST is None:
        WEB_SERVICE_HOST = '127.0.0.1'

    logger.info('Starting WebSocket Server')
    logger.debug(f'Using redis host: {REDIS_HOST}, redis port: {REDIS_PORT}, RabbitMQ host: {RABBITMQ_HOST}, web service host: {WEB_SERVICE_HOST}')

    WebSocketServer(REDIS_HOST, REDIS_PORT, RABBITMQ_HOST, WEB_SERVICE_HOST)
