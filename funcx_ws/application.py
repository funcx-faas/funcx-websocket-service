import os
from funcx_ws.server import WebSocketServer

def run():
    REDIS_HOST = os.environ.get('REDIS_HOST')
    REDIS_PORT = os.environ.get('REDIS_PORT')

    if REDIS_HOST is None:
        REDIS_HOST = '127.0.0.1'

    if REDIS_PORT is None:
        REDIS_PORT = 6379

    WebSocketServer(REDIS_HOST, REDIS_PORT)
