import os
import argparse
import logging
from funcx_websocket_service.application import run
from funcx_websocket_service.utils.loggers import set_stream_logger

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Debug logging")

    args = parser.parse_args()

    env_debug = os.environ.get('FUNCX_WEBSOCKET_SERVICE_DEBUG')

    debug = args.debug is True or env_debug is not None
    set_stream_logger(level=logging.DEBUG if debug else logging.INFO)

    run()

if __name__ == '__main__':
    main()
