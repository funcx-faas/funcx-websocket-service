import os
from funcx_ws.server import WebSocketServer


def run():
    REDIS_HOST = os.environ.get('REDIS_HOST')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    GLOBUS_CLIENT = os.environ.get('GLOBUS_CLIENT')
    GLOBUS_KEY = os.environ.get('GLOBUS_KEY')

    if REDIS_HOST is None:
        REDIS_HOST = '127.0.0.1'

    if REDIS_PORT is None:
        REDIS_PORT = 6379

    if GLOBUS_CLIENT is None or GLOBUS_KEY is None:
        raise Exception('GLOBUS_CLIENT and GLOBUS_KEY environment variables must be set')

    WebSocketServer(REDIS_HOST, REDIS_PORT, GLOBUS_CLIENT, GLOBUS_KEY)
